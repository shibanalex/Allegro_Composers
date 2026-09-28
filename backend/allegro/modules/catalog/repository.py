"""Queries of the catalog module (no commits here: transactions belong to the service)"""
import uuid
from typing import Optional

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.orm import Session

from allegro.modules.accounts.service import authors_matching, author_named, visible_authors
from allegro.modules.catalog.models import Collection, Opus, Performance


def opus_by_slug(db: Session, slug: str) -> Optional[Opus]:
    return db.scalar(select(Opus).where(Opus.slug == slug))


def opus_page(
    db: Session, *, author_username: Optional[str], owner_id: Optional[uuid.UUID], ensemble=None, form=None, key=None,
    difficulty=None, tag=None, q=None, featured: Optional[bool] = None, sort="new", limit=20, offset=0,
) -> tuple[list[Opus], int]:
    """Published works of visible authors (or all of the owner's own, drafts included)"""
    stmt = select(Opus)
    if owner_id:
        stmt = stmt.where(Opus.author_id == owner_id)
    else:
        stmt = stmt.where(Opus.status == "published", visible_authors(Opus.author_id))
    if author_username:
        stmt = stmt.where(author_named(Opus.author_id, author_username))
    if ensemble:
        stmt = stmt.where(Opus.ensemble == ensemble)
    if form:
        stmt = stmt.where(Opus.form == form)
    if key:
        stmt = stmt.where(Opus.key_signature == key)
    if difficulty:
        stmt = stmt.where(Opus.difficulty == difficulty)
    if featured is not None:
        stmt = stmt.where(Opus.featured.is_(featured))
    if tag:
        stmt = stmt.where(func.lower(cast(Opus.tags, String)).contains(f'"{tag.strip().lower()}"', autoescape=True))
    if q and q.strip():
        needle = q.strip().lower()
        stmt = stmt.where(or_(
            func.lower(Opus.title).contains(needle, autoescape=True),
            func.lower(Opus.subtitle).contains(needle, autoescape=True),
            func.lower(Opus.instrumentation).contains(needle, autoescape=True),
            func.lower(Opus.key_signature).contains(needle, autoescape=True),
            func.lower(cast(Opus.tags, String)).contains(needle, autoescape=True),
            authors_matching(Opus.author_id, needle),
        ))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = {
        "new": [Opus.created_at.desc()],
        "popular": [Opus.play_count.desc(), Opus.created_at.desc()],
        "title": [Opus.title.asc()],
    }[sort]
    items = list(db.scalars(stmt.order_by(*order).offset(offset).limit(limit)).unique())
    return items, total


def facet_rows(db: Session, author_id: Optional[uuid.UUID] = None):
    stmt = select(Opus.ensemble, Opus.form, Opus.key_signature, Opus.difficulty, Opus.tags).where(
        Opus.status == "published", visible_authors(Opus.author_id),
    )
    if author_id:
        stmt = stmt.where(Opus.author_id == author_id)
    return db.execute(stmt).all()


def collections_of(db: Session, author_id: uuid.UUID) -> list[Collection]:
    return list(db.scalars(
        select(Collection).where(Collection.author_id == author_id).order_by(Collection.year.desc(), Collection.created_at.desc())
    ))


def own_opus_ids(db: Session, author_id: uuid.UUID, ids: list[uuid.UUID]) -> set[uuid.UUID]:
    return set(db.scalars(select(Opus.id).where(Opus.id.in_(ids), Opus.author_id == author_id)))


def performance_page(
    db: Session, *, performer_id: Optional[uuid.UUID] = None, opus_id: Optional[uuid.UUID] = None,
    include_drafts_of: Optional[uuid.UUID] = None, limit=20, offset=0,
) -> tuple[list[Performance], int]:
    stmt = select(Performance)
    if include_drafts_of:
        stmt = stmt.where(or_(Performance.status == "published", Performance.performer_id == include_drafts_of))
    else:
        stmt = stmt.where(Performance.status == "published")
    stmt = stmt.where(visible_authors(Performance.performer_id))
    if performer_id:
        stmt = stmt.where(Performance.performer_id == performer_id)
    if opus_id:
        stmt = stmt.where(Performance.opus_id == opus_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(Performance.created_at.desc()).offset(offset).limit(limit)).unique())
    return items, total


def count_by(db: Session, column, ids: list[uuid.UUID], *where) -> dict[uuid.UUID, int]:
    return dict(db.execute(select(column, func.count()).where(column.in_(ids), *where).group_by(column)).all())
