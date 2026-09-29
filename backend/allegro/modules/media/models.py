"""Tables owned by the media module"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from allegro.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Upload(Base):
    """Every stored upload: who, how big, when — for the daily limit of each member (storage is paid for)"""
    __tablename__ = "uploads"

    key: Mapped[str] = mapped_column(String(512), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    size: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
