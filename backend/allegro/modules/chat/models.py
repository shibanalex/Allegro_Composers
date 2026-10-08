"""Tables owned by the chat module"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from allegro.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ChatMessage(Base):
    """One message of the chat. `room` is «general» for now: other rooms would need no new table."""
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_room_created", "room", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    room: Mapped[str] = mapped_column(String(40), default="general")
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    author = relationship("User", lazy="joined")
