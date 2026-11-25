"""Tables owned by the catalog module: works (opuses) with their score sync, collections, performances"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from allegro.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Opus(Base):
    __tablename__ = "opuses"
    # A composer's works newest first (hall, library) and the feed of new works
    __table_args__ = (Index("ix_opuses_author_status_created", "author_id", "status", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    subtitle: Mapped[Optional[str]] = mapped_column(String(255))  # "op. 1, Ч. I: Allegro"
    genre: Mapped[str] = mapped_column(String(20), index=True, default="other")  # enums.GENRES: «Трио», «Концерт»…
    instruments: Mapped[list] = mapped_column(JSON, default=list)  # ["скрипка", "виолончель", "фортепиано"]
    key_signature: Mapped[Optional[str]] = mapped_column(String(40), index=True)
    year: Mapped[Optional[int]] = mapped_column(Integer)
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
    # Shown on the composer's «Выставка» (the showcase); the «Библиотека» catalogue lists every work
    featured: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    author = relationship("User", lazy="joined")
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


class Performance(Base):
    """A recording of a piece by a member: one of the site's works (opus_id) or any other («Шопен: Баллада №1»)"""
    __tablename__ = "performances"
    __table_args__ = (Index("ix_performances_performer_created", "performer_id", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    performer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(255))  # what is performed
    composer_name: Mapped[Optional[str]] = mapped_column(String(160))  # when the work isn't on the site
    opus_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("opuses.id", ondelete="SET NULL"), index=True)
    description_md: Mapped[Optional[str]] = mapped_column(Text)
    audio_type: Mapped[str] = mapped_column(String(20))  # youtube | hosted_file
    audio_source: Mapped[str] = mapped_column(String(512))  # YouTube id or storage key
    audio_duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    recorded_year: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="published", index=True)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    performer = relationship("User", lazy="joined")
    opus: Mapped[Optional[Opus]] = relationship(lazy="joined")
