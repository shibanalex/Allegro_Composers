"""Discussion service: critiques on opuses (with timecodes) and threaded comments on posts"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from allegro_common.db import get_db
from allegro_common.deps import get_current_user, get_optional_user
from allegro_common.models import Comment, Opus, Post, User
from allegro_common.schemas import ORMModel, UserBrief, UTCDateTime

router = APIRouter(tags=["discussion"])


class CommentIn(BaseModel):
    opus_id: Optional[uuid.UUID] = None
    post_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    timestamp_marker: Optional[float] = Field(None, ge=0)
    content_md: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def _single_target(self):
        if (self.opus_id is None) == (self.post_id is None):
            raise ValueError("Укажите либо opus_id, либо post_id")
        return self


class CommentOut(ORMModel):
    id: uuid.UUID
    opus_id: Optional[uuid.UUID] = None
    post_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    timestamp_marker: Optional[float] = None
    content_md: str
    created_at: UTCDateTime
    author: UserBrief


def _target(db: Session, opus_id, post_id, user: Optional[User]):
    """The opus or post being discussed; drafts are only visible to their author"""
    target = db.get(Opus, opus_id) if opus_id else db.get(Post, post_id)
    if not target or (target.status == "draft" and (not user or user.id != target.author_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Не найдено")
    return target


@router.get("/api/comments", response_model=list[CommentOut])
def list_comments(
    opus_id: Optional[uuid.UUID] = None,
    post_id: Optional[uuid.UUID] = None,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Flat list in chronological order; the client builds the tree from parent_id"""
    if (opus_id is None) == (post_id is None):
        raise HTTPException(422, "Укажите либо opus_id, либо post_id")
    _target(db, opus_id, post_id, user)
    column = Comment.opus_id if opus_id else Comment.post_id
    return db.scalars(select(Comment).where(column == (opus_id or post_id)).order_by(Comment.created_at)).all()


@router.post("/api/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(data: CommentIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    target = _target(db, data.opus_id, data.post_id, user)
    if data.parent_id:
        parent = db.get(Comment, data.parent_id)
        if not parent or parent.opus_id != data.opus_id or parent.post_id != data.post_id:
            raise HTTPException(422, "Ответ должен относиться к тому же обсуждению")
    # Timecodes refer to a recording: the opus itself or the opus a workshop thread is about
    if data.timestamp_marker is not None and data.post_id and not target.opus_id:
        raise HTTPException(422, "У этой публикации нет записи для таймкода")
    comment = Comment(author_id=user.id, **data.model_dump())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/api/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """The commenter or the owner of the opus/post may delete (replies go with it)"""
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Комментарий не найден")
    target = db.get(Opus, comment.opus_id) if comment.opus_id else db.get(Post, comment.post_id)
    if user.id not in (comment.author_id, target.author_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нельзя удалить чужой комментарий")
    db.delete(comment)
    db.commit()
