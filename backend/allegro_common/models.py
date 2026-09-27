"""Database schema shared by all services.

Services own their endpoints, not their tables: every service may read any table
(e.g. catalog counts critiques, discussion checks that an opus exists).
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from allegro_common.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    pseudonym: Mapped[Optional[str]] = mapped_column(String(120))
    bio: Mapped[Optional[str]] = mapped_column(String(400))  # short manifesto shown in the salon header
    about_md: Mapped[Optional[str]] = mapped_column(Text)  # full biography / CV
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512))
    links: Mapped[list] = mapped_column(JSON, default=list)  # [{label, url}]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Opus(Base):
    __tablename__ = "opuses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    subtitle: Mapped[Optional[str]] = mapped_column(String(255))  # "op. 1, Ч. I: Allegro"
    instrumentation: Mapped[Optional[str]] = mapped_column(String(255))  # "Ф-но, Скрипка, Вч."
    ensemble: Mapped[str] = mapped_column(String(20), index=True)  # enums.ENSEMBLES
    form: Mapped[str] = mapped_column(String(20), index=True)  # enums.FORMS
    key_signature: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    difficulty: Mapped[Optional[int]] = mapped_column(Integer)  # 1..5
    year: Mapped[Optional[int]] = mapped_column(Integer)
    tags: Mapped[list] = mapped_column(JSON, default=list)  # instrument / free tags
    description_md: Mapped[Optional[str]] = mapped_column(Text)  # explication / analysis
    cover_url: Mapped[Optional[str]] = mapped_column(String(512))

    audio_type: Mapped[str] = mapped_column(String(20), default="none")  # none | youtube | hosted_file
    audio_source: Mapped[Optional[str]] = mapped_column(String(512))  # YouTube id or storage key
    audio_duration_seconds: Mapped[Optional[float]] = mapped_column(Float)

    score_file_key: Mapped[Optional[str]] = mapped_column(String(512))
    score_page_count: Mapped[Optional[int]] = mapped_column(Integer)
    score_access: Mapped[str] = mapped_column(String(20), default="free")  # enums.SCORE_ACCESS (PDF and MusicXML)

    # Interactive score: MusicXML (.musicxml/.xml) or compressed MusicXML (.mxl) with a playback cursor
    musicxml_file_key: Mapped[Optional[str]] = mapped_column(String(512))
    # Second of the recording where the first beat of the score sounds
    audio_offset_seconds: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    # PDF page-turn markers derived from the MusicXML page layout (True) or set by hand (False)
    auto_page_markers: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")

    status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    author: Mapped[User] = relationship(lazy="joined")
    markers: Mapped[list["ScoreSyncMarker"]] = relationship(
        order_by="ScoreSyncMarker.page_number", cascade="all, delete-orphan", lazy="selectin",
    )
    measure_markers: Mapped[list["MeasureSyncMarker"]] = relationship(
        order_by="MeasureSyncMarker.measure_number", cascade="all, delete-orphan", lazy="selectin",
    )


class ScoreSyncMarker(Base):
    """Page N of the score starts at timestamp_seconds of the recording"""
    __tablename__ = "score_sync_markers"
    __table_args__ = (UniqueConstraint("opus_id", "page_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opus_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("opuses.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    timestamp_seconds: Mapped[float] = mapped_column(Float)


class MeasureSyncMarker(Base):
    """Measure N of the MusicXML score starts at timestamp_seconds of the recording.

    Optional: without markers the cursor follows the tempo written in the file (plus audio_offset_seconds);
    markers pin a live performance with rubato - the cursor interpolates between them.
    """
    __tablename__ = "measure_sync_markers"
    __table_args__ = (UniqueConstraint("opus_id", "measure_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opus_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("opuses.id", ondelete="CASCADE"), index=True)
    measure_number: Mapped[int] = mapped_column(Integer)
    timestamp_seconds: Mapped[float] = mapped_column(Float)


class Collection(Base):
    """A cycle or collection of works: «Цикл "Флориография" (2026)»"""
    __tablename__ = "collections"
    __table_args__ = (UniqueConstraint("author_id", "slug"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    year: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    items: Mapped[list["CollectionItem"]] = relationship(
        order_by="CollectionItem.position", cascade="all, delete-orphan", lazy="selectin",
    )


class CollectionItem(Base):
    __tablename__ = "collection_items"

    collection_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True)
    opus_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("opuses.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    opus: Mapped[Opus] = relationship(lazy="joined")


class Post(Base):
    """Articles (theory), personal notes (blog) and workshop threads (review requests)"""
    __tablename__ = "posts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)  # enums.POST_KINDS
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    excerpt: Mapped[Optional[str]] = mapped_column(String(512))
    content_md: Mapped[str] = mapped_column(Text)
    cover_url: Mapped[Optional[str]] = mapped_column(String(512))
    attachments: Mapped[list] = mapped_column(JSON, default=list)  # [{url, name, content_type, size}]
    tags: Mapped[list] = mapped_column(JSON, default=list)
    opus_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("opuses.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    author: Mapped[User] = relationship(lazy="joined")
    opus: Mapped[Optional[Opus]] = relationship(lazy="joined")


class Material(Base):
    """An item in a composer's «Материалы»: a book, a link or a file (with a description)"""
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


class Comment(Base):
    """Critiques on an opus or comments on a post; tree via parent_id"""
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

    author: Mapped[User] = relationship(lazy="joined")
