"""Tables owned by the notifications module"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from allegro.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Notification(Base):
    """One member learns about one new publication. Written in bulk by the worker, read by the bell."""
    __tablename__ = "notifications"
    # the bell: a member's newest first, and how many are unread
    __table_args__ = (Index("ix_notifications_user_created", "user_id", "created_at"),
                      Index("ix_notifications_target", "target_type", "target_id"))

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(20))  # opus | sketch | article | performance | note | news | workshop
    target_type: Mapped[str] = mapped_column(String(20))  # opus | performance | post
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid)
    title: Mapped[str] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    actor = relationship("User", foreign_keys=[actor_id], lazy="joined")


class NotificationSettings(Base):
    """What a member wants to hear about and how; no row — the defaults"""
    __tablename__ = "notification_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    kinds: Mapped[list] = mapped_column(JSON, default=list)  # kinds of publications; empty — all of them
    push: Mapped[bool] = mapped_column(Boolean, default=True)
    email: Mapped[str] = mapped_column(String(10), default="off")  # off | daily | weekly
    last_digest_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class PushSubscription(Base):
    """A browser (a device) that agreed to receive push notifications"""
    __tablename__ = "push_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    endpoint: Mapped[str] = mapped_column(String(1024), unique=True)
    p256dh: Mapped[str] = mapped_column(String(255))
    auth: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
