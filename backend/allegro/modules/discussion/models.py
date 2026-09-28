"""Tables owned by the discussion module"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from allegro.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Comment(Base):
    """Critiques on an opus or comments on a post; tree via parent_id.

    The targets live in other modules; this table only refers to them by id (one database, one schema).
    """
    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint("(opus_id IS NULL) <> (post_id IS NULL)", name="comment_single_target"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    opus_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("opuses.id", ondelete="CASCADE"), index=True)
    post_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"))
    timestamp_marker: Mapped[Optional[float]] = mapped_column(Float)  # second of the recording
    content_md: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    author = relationship("User", lazy="joined")
