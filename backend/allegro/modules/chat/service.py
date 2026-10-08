"""Use cases of the chat module.

A message is saved first and published to the live channel after the commit (core.realtime): the database
is the history, Centrifugo only delivers. Mentions (@address) go through the outbox like every other event
(core.events «mentioned»), so the notifications module tells the mentioned members — the chat knows nothing
about the bell. Deleting a message also deletes the notifications about it («removed»).
"""
import re
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from allegro.core import realtime
from allegro.core.db import after_commit
from allegro.core.errors import Forbidden, NotFound
from allegro.core.events import emit
from allegro.core.ratelimit import AttemptLimiter
from allegro.modules.accounts.roles import Capability, can
from allegro.modules.accounts.service import ids_by_usernames, visible_authors
from allegro.modules.chat.models import ChatMessage
from allegro.modules.chat.schemas import MessageOut, MessagePage

ROOM = "general"
CHANNEL = f"chat:{ROOM}"
MAX_MENTIONS = 10
# @ivan_petrov, @anna.k: a hall address after «@», not inside an e-mail address
MENTION = re.compile(r"(?<![\w.@])@([a-z0-9][a-z0-9._-]{1,30}[a-z0-9])", re.IGNORECASE)
# One member: no more than 20 messages a minute (a flood would bury the conversation)
pace = AttemptLimiter(20, 60, "Слишком часто — подождите немного.")


def history(db: Session, before: Optional[uuid.UUID], limit: int) -> MessagePage:
    """The latest messages (or the ones before `before`), oldest first"""
    limit = min(max(limit, 1), 100)
    stmt = select(ChatMessage).where(ChatMessage.room == ROOM, visible_authors(ChatMessage.author_id))
    if before:
        pivot = db.get(ChatMessage, before)
        if pivot:
            stmt = stmt.where(ChatMessage.created_at < pivot.created_at)
    rows = list(db.scalars(stmt.order_by(ChatMessage.created_at.desc()).limit(limit + 1)))
    more = len(rows) > limit
    rows = rows[:limit][::-1]
    return MessagePage(items=[MessageOut.model_validate(m) for m in rows], next_before=str(rows[0].id) if more and rows else None)


def mentioned_usernames(text: str) -> list[str]:
    return list(dict.fromkeys(m.lower() for m in MENTION.findall(text)))[:MAX_MENTIONS]


def post(db: Session, user, text: str) -> MessageOut:
    pace.check((str(user.id),))
    pace.hit((str(user.id),))
    message = ChatMessage(room=ROOM, author_id=user.id, text=text)
    db.add(message)
    db.flush()
    mentioned = [i for i in ids_by_usernames(db, mentioned_usernames(text)).values() if i != user.id]
    if mentioned:
        emit(db, "mentioned", author_id=user.id, user_ids=",".join(str(i) for i in mentioned), id=message.id,
             target_type="chat", title=text[:200], url=f"/?feed=chat#m-{message.id}")
    db.commit()
    db.refresh(message)
    out = MessageOut.model_validate(message)
    realtime.publish(CHANNEL, {"type": "message", "message": out.model_dump(mode="json")})
    return out


def delete(db: Session, user, message_id: uuid.UUID) -> None:
    """The author, or a moderator"""
    message = db.get(ChatMessage, message_id)
    if not message:
        raise NotFound("Сообщение не найдено")
    if message.author_id != user.id and not can(user, Capability.MODERATE):
        raise Forbidden("Удалить можно только своё сообщение")
    emit(db, "removed", target_type="chat", id=message.id)
    db.delete(message)
    after_commit(db, lambda: realtime.publish(CHANNEL, {"type": "deleted", "id": str(message_id)}))
    db.commit()


def connection(user) -> dict:
    return {"url": "/connection/websocket", "token": realtime.connection_token(str(user.id) if user else None), "channel": CHANNEL}
