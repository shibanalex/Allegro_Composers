"""Use cases of the discussion module.

The module doesn't know what an opus or a post is. The modules that own them register a *target
resolver* at start-up (see allegro.main): given an id and the reader, it says whether the thing exists
and is visible, who owns it and whether it has a recording that timecodes could refer to. So the
dependency points one way — catalog and publications use discussion, never the other way round.

Public API: `register_target`, `count_comments`.
"""
import uuid
from dataclasses import dataclass
from typing import Callable, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from allegro.core.errors import Forbidden, Invalid, NotFound
from allegro.modules.accounts.service import visible_authors
from allegro.modules.discussion.models import Comment
from allegro.modules.discussion.schemas import CommentIn

TARGET_COLUMNS = {"opus": Comment.opus_id, "post": Comment.post_id}


@dataclass(frozen=True)
class Target:
    owner_id: uuid.UUID
    has_recording: bool  # timecodes in comments can be played


TargetResolver = Callable[[Session, uuid.UUID, Optional[object]], Optional[Target]]
_resolvers: dict[str, TargetResolver] = {}


def register_target(kind: str, resolver: TargetResolver) -> None:
    _resolvers[kind] = resolver


def _target(db: Session, kind: str, target_id: uuid.UUID, user) -> Target:
    target = _resolvers[kind](db, target_id, user)
    if not target:
        raise NotFound("Не найдено")
    return target


def _kind_of(data_or_comment) -> tuple[str, uuid.UUID]:
    return ("opus", data_or_comment.opus_id) if data_or_comment.opus_id else ("post", data_or_comment.post_id)


def count_comments(db: Session, kind: str, ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not ids:
        return {}
    column = TARGET_COLUMNS[kind]
    return dict(db.execute(select(column, func.count()).where(column.in_(ids)).group_by(column)).all())


def list_comments(db: Session, kind: str, target_id: uuid.UUID, user) -> list[Comment]:
    """Flat list in chronological order; the client builds the tree from parent_id"""
    _target(db, kind, target_id, user)
    column = TARGET_COLUMNS[kind]
    # Critiques written by shadowed accounts are hidden too
    return list(db.scalars(
        select(Comment).where(column == target_id, visible_authors(Comment.author_id)).order_by(Comment.created_at)
    ))


def create_comment(db: Session, user, data: CommentIn) -> Comment:
    kind, target_id = _kind_of(data)
    target = _target(db, kind, target_id, user)
    if data.parent_id:
        parent = db.get(Comment, data.parent_id)
        if not parent or parent.opus_id != data.opus_id or parent.post_id != data.post_id:
            raise Invalid("Ответ должен относиться к тому же обсуждению")
    # Timecodes refer to a recording
    if data.timestamp_marker is not None and not target.has_recording:
        raise Invalid("У этой публикации нет записи для таймкода")
    comment = Comment(author_id=user.id, **data.model_dump())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def delete_comment(db: Session, user, comment_id: uuid.UUID) -> None:
    """The commenter or the owner of the opus/post may delete (replies go with it)"""
    comment = db.get(Comment, comment_id)
    if not comment:
        raise NotFound("Комментарий не найден")
    kind, target_id = _kind_of(comment)
    resolver = _resolvers[kind](db, target_id, user)
    owner_id = resolver.owner_id if resolver else None
    if user.id not in (comment.author_id, owner_id) and not user.is_admin:
        raise Forbidden("Нельзя удалить чужой комментарий")
    db.delete(comment)
    db.commit()
