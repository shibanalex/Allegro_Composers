"""The outbox: events that other parts of the site react to later (notifications first of all).

A module that publishes something calls `emit(db, "published", ...)` inside its own transaction: the event
is saved together with the post or work, or not at all. A worker (allegro.modules.notifications.worker)
takes pending events in order and handles them; a failed one is retried a few times.

This is the «broker» in the database: nothing to host, nothing lost on a restart. When one database stops
being enough, the table is replaced by Redis Streams or RabbitMQ behind the same `emit`.
"""
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from allegro.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OutboxEvent(Base):
    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(40))  # published | removed
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[Optional[str]] = mapped_column(Text)


def emit(db: Session, event: str, /, **payload: Any) -> None:
    """Record an event in the caller's transaction (it is saved with the caller's commit, or not at all)"""
    db.add(OutboxEvent(kind=event, payload={k: (str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v)
                                           for k, v in payload.items()}))
