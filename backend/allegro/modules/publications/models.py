"""Tables owned by the publications module: posts and members' materials"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from allegro.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Post(Base):
    """Blog posts (notes), articles and reviews, the site's news, and old workshop threads (review requests)"""
    __tablename__ = "posts"
    # A member's posts of one kind, newest first (hall tabs), and the feeds
    __table_args__ = (Index("ix_posts_author_kind_created", "author_id", "kind", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # note | article | news | workshop
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    excerpt: Mapped[Optional[str]] = mapped_column(String(512))
    content_md: Mapped[str] = mapped_column(Text)
    cover_url: Mapped[Optional[str]] = mapped_column(String(512))
    attachments: Mapped[list] = mapped_column(JSON, default=list)  # [{url, name, content_type, size}]
    tags: Mapped[list] = mapped_column(JSON, default=list)
    opus_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("opuses.id", ondelete="SET NULL"))
    # A post quoting another one, like a repost with one's own words; the quoted post may disappear later
    quote_post_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("posts.id", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    author = relationship("User", lazy="joined")
    opus = relationship("Opus", lazy="joined")
    quote = relationship("Post", remote_side=[id], lazy="joined", join_depth=1)


class PostLink(Base):
    """A post's text links to another post or a work (…/posts/<slug>, …/opus/<slug>).

    Worked out once, when the post is saved, so a page can show «упоминания» without reading any texts.
    """
    __tablename__ = "post_links"

    post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    target_kind: Mapped[str] = mapped_column(String(20), primary_key=True)  # post | opus
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)

    __table_args__ = (Index("ix_post_links_target", "target_kind", "target_id"),)


class Material(Base):
    """An item in a member's «Материалы»: a book, a link or a file (with a description)"""
    __tablename__ = "materials"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # enums.MATERIAL_KINDS
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(1024))  # external link (site, shop, library…)
    file: Mapped[Optional[dict]] = mapped_column(JSON)  # {url, name, content_type, size}
    cover_url: Mapped[Optional[str]] = mapped_column(String(512))
    position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
