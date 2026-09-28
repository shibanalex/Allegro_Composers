"""HTTP layer of the discussion module: critiques on opuses (with timecodes) and threaded comments on posts"""
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from allegro.core.db import get_db
from allegro.core.errors import Invalid
from allegro.modules.accounts.deps import get_current_user, get_optional_user, require
from allegro.modules.accounts.roles import Capability
from allegro.modules.discussion import service
from allegro.modules.discussion.schemas import CommentIn, CommentOut, ReactionsOut

ReactionKind = Literal["opus", "post", "performance"]

router = APIRouter(tags=["discussion"])


@router.get("/api/comments", response_model=list[CommentOut])
def list_comments(
    opus_id: Optional[uuid.UUID] = None,
    post_id: Optional[uuid.UUID] = None,
    user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if (opus_id is None) == (post_id is None):
        raise Invalid("Укажите либо opus_id, либо post_id")
    return service.list_comments(db, "opus" if opus_id else "post", opus_id or post_id, user)


@router.post("/api/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(data: CommentIn, user=Depends(require(Capability.COMMENT)), db: Session = Depends(get_db)):
    return service.create_comment(db, user, data)


@router.delete("/api/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(comment_id: uuid.UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service.delete_comment(db, user, comment_id)


# ---------------------------------------------------------------- «нравится»

@router.put("/api/reactions/{kind}/{target_id}", response_model=ReactionsOut)
def like(kind: ReactionKind, target_id: uuid.UUID, user=Depends(require(Capability.REACT)), db: Session = Depends(get_db)):
    return service.set_reaction(db, user, kind, target_id, on=True).__dict__


@router.delete("/api/reactions/{kind}/{target_id}", response_model=ReactionsOut)
def unlike(kind: ReactionKind, target_id: uuid.UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.set_reaction(db, user, kind, target_id, on=False).__dict__


@router.get("/api/reactions/{kind}", response_model=dict[uuid.UUID, ReactionsOut])
def reactions(kind: ReactionKind, ids: str, user=Depends(get_optional_user), db: Session = Depends(get_db)):
    """Likes of several things at once (?ids=a,b,c) — for pages that aren't the feed"""
    try:
        wanted = [uuid.UUID(i) for i in ids.split(",") if i][:100]
    except ValueError:
        raise Invalid("Неверный список")
    return {i: r.__dict__ for i, r in service.reaction_summary(db, kind, wanted, user).items()}
