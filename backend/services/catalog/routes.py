"""Catalog service: opuses with score sync markers, collections, library facets, global search"""
import uuid
from collections import Counter
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import String, cast, func, or_, select, update
from sqlalchemy.orm import Session

from allegro_common import enums
from allegro_common.db import get_db
from allegro_common.musicxml import page_start_times
from allegro_common.deps import get_current_user, get_optional_user
from allegro_common.media_refs import check_key, check_url, delete_own
from allegro_common.media_refs import check_key, check_url, delete_own
from allegro_common.models import (
    Collection, CollectionItem, Comment, MeasureSyncMarker, Opus, Post, ScoreSyncMarker, User,
)
from allegro_common.storage import storage
from allegro_common.utils import unique_slug, visible_authors
from services.catalog.schemas import (
    YOUTUBE_ID, CollectionIn, CollectionOut, CollectionUpdate, Facet, Facets, Marker, MeasureMarker, OpusCreate, OpusOut,
    OpusPage, OpusUpdate, SearchComposer, SearchOpus, SearchPost, SearchResult,
)

router = APIRouter(tags=["catalog"])


# ---------------------------------------------------------------- helpers

def _critique_counts(db: Session, ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not ids:
        return {}
    rows = db.execute(
        select(Comment.opus_id, func.count()).where(Comment.opus_id.in_(ids)).group_by(Comment.opus_id)
    )
    return dict(rows.all())


def _out(opus: Opus, counts: Optional[dict] = None) -> OpusOut:
    out = OpusOut.model_validate(opus)
    return out.model_copy(update={
        "audio_url": storage.url(opus.audio_source) if opus.audio_type == "hosted_file" else None,
        "score_url": storage.url(opus.score_file_key),
        "musicxml_url": storage.url(opus.musicxml_file_key),
        "critique_count": (counts or {}).get(opus.id, 0),
    })


def _outs(db: Session, opuses: list[Opus]) -> list[OpusOut]:
    counts = _critique_counts(db, [o.id for o in opuses])
    return [_out(o, counts) for o in opuses]


def _visible(opus: Optional[Opus], user: Optional[User]) -> bool:
    if not opus or opus.author.is_hidden:  # works of shadowed accounts vanish from the site
        return False
    return opus.status != "draft" or (user is not None and user.id == opus.author_id)


def _get_opus(db: Session, slug: str, user: Optional[User]) -> Opus:
    opus = db.scalar(select(Opus).where(Opus.slug == slug))
    if not _visible(opus, user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Опус не найден")
    return opus


def _own_opus(db: Session, slug: str, user: User) -> Opus:
    opus = _get_opus(db, slug, user)
    if opus.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Это не ваш опус")
    return opus


def _normalize_audio(values: dict) -> None:
    """Validate audio fields in-place; accepts a full YouTube URL and stores only the video id"""
    audio_type = values.get("audio_type")
    source = (values.get("audio_source") or "").strip() or None
    if audio_type == "youtube":
        match = YOUTUBE_ID.search(source or "")
        video_id = match.group(1) if match else source
        if not video_id or len(video_id) != 11:
            raise HTTPException(422, "Укажите ссылку на YouTube или id видео")
        values["audio_source"] = video_id
    elif audio_type == "hosted_file":
        if not source:
            raise HTTPException(422, "Загрузите аудиофайл")
        values["audio_source"] = source
    elif audio_type == "none":
        values["audio_source"] = None


def _check_files(user: User, values: dict, opus: Optional[Opus] = None) -> None:
    """Score, MusicXML, audio and cover must be the author's own uploads (or already on this opus)"""
    for field in ("score_file_key", "musicxml_file_key"):
        if field in values:
            check_key(user, values[field], [getattr(opus, field, None)])
    if values.get("audio_type") == "hosted_file":
        check_key(user, values.get("audio_source"), [getattr(opus, "audio_source", None)])
    if "cover_url" in values:
        check_url(user, values["cover_url"], [getattr(opus, "cover_url", None)])


def _check_files(user: User, values: dict, opus: Optional[Opus] = None) -> None:
    """Score, MusicXML, audio and cover must be the author's own uploads (or already on this opus)"""
    for field in ("score_file_key", "musicxml_file_key"):
        if field in values:
            check_key(user, values[field], [getattr(opus, field, None)])
    if values.get("audio_type") == "hosted_file":
        check_key(user, values.get("audio_source"), [getattr(opus, "audio_source", None)])
    if "cover_url" in values:
        check_url(user, values["cover_url"], [getattr(opus, "cover_url", None)])


def _check_markers(markers: list[Marker], page_count: Optional[int]) -> None:
    pages = [m.page_number for m in markers]
    if len(pages) != len(set(pages)):
        raise HTTPException(422, "У каждой страницы может быть только одна отметка")
    if page_count and any(p > page_count for p in pages):
        raise HTTPException(422, f"В партитуре всего {page_count} стр.")


def _set_markers(db: Session, opus: Opus, markers: list[Marker]) -> None:
    if opus.markers:
        # Delete old rows before inserting new ones: (opus_id, page_number) is unique
        opus.markers.clear()
        db.flush()
    opus.markers = [
        ScoreSyncMarker(page_number=m.page_number, timestamp_seconds=m.timestamp_seconds)
        for m in sorted(markers, key=lambda m: m.page_number)
    ]


def _check_measure_markers(markers: list[MeasureMarker]) -> None:
    ordered = sorted(markers, key=lambda m: m.measure_number)
    if len({m.measure_number for m in markers}) != len(markers):
        raise HTTPException(422, "У каждого такта может быть только одна отметка")
    if any(b.timestamp_seconds <= a.timestamp_seconds for a, b in zip(ordered, ordered[1:])):
        raise HTTPException(422, "Отметки тактов должны идти по возрастанию времени")


def _set_measure_markers(db: Session, opus: Opus, markers: list[MeasureMarker]) -> None:
    if opus.measure_markers:
        opus.measure_markers.clear()
        db.flush()
    opus.measure_markers = [
        MeasureSyncMarker(measure_number=m.measure_number, timestamp_seconds=m.timestamp_seconds)
        for m in sorted(markers, key=lambda m: m.measure_number)
    ]


def _sync_page_markers(db: Session, opus: Opus) -> None:
    """Auto mode: PDF pages turn where the MusicXML page breaks sound (written tempo + offset / measure markers)"""
    if not opus.auto_page_markers:
        return
    times = None
    if opus.musicxml_file_key and opus.score_page_count and opus.audio_type != "none":
        try:
            times = page_start_times(
                storage.read_bytes(opus.musicxml_file_key), opus.score_page_count, opus.audio_offset_seconds or 0,
                [(m.measure_number, m.timestamp_seconds) for m in opus.measure_markers],
            )
        except Exception:  # unreadable or unusual MusicXML: simply no automatic page turns
            times = None
    _set_markers(db, opus, [Marker(page_number=i + 1, timestamp_seconds=t) for i, t in enumerate(times or [])])


def _download(opus: Opus, key: Optional[str], user: Optional[User], media_type: str, suffix: str) -> StreamingResponse:
    """Score files honour the author's choice: free / view only / paid"""
    if not key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Файла нет")
    is_author = user is not None and user.id == opus.author_id
    if opus.score_access != "free" and not is_author:
        detail = "Партитура доступна только для просмотра" if opus.score_access == "view_only" else "Скачивание за донат появится позже"
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail)
    chunks = storage.open_stream(key)
    if chunks is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Файл не найден")
    return StreamingResponse(
        chunks, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{opus.slug}{suffix}"'},
    )


# ---------------------------------------------------------------- opuses

@router.get("/api/opuses", response_model=OpusPage)
def list_opuses(
    author: Optional[str] = None,
    ensemble: Optional[str] = None,
    form: Optional[str] = None,
    key: Optional[str] = None,
    difficulty: Optional[int] = Query(None, ge=1, le=5),
    tag: Optional[str] = None,
    q: Optional[str] = None,
    sort: Literal["new", "popular", "title"] = "new",
    mine: bool = False,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Feed «Все опусы» and the library catalogue. `mine=true` includes the caller's drafts."""
    stmt = select(Opus).join(Opus.author)
    if mine:
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется вход")
        stmt = stmt.where(Opus.author_id == user.id)
    else:
        stmt = stmt.where(Opus.status == "published", User.is_hidden.is_(False))
    if author:
        stmt = stmt.where(User.username == author.lower())
    if ensemble:
        stmt = stmt.where(Opus.ensemble == ensemble)
    if form:
        stmt = stmt.where(Opus.form == form)
    if key:
        stmt = stmt.where(Opus.key_signature == key)
    if difficulty:
        stmt = stmt.where(Opus.difficulty == difficulty)
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
            func.lower(User.display_name).contains(needle, autoescape=True),
        ))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    order = {
        "new": [Opus.created_at.desc()],
        "popular": [Opus.play_count.desc(), Opus.created_at.desc()],
        "title": [Opus.title.asc()],
    }[sort]
    opuses = db.scalars(stmt.order_by(*order).offset(offset).limit(limit)).unique().all()
    return OpusPage(items=_outs(db, list(opuses)), total=total)


@router.get("/api/opuses/{slug}", response_model=OpusOut)
def get_opus(slug: str, user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    opus = _get_opus(db, slug, user)
    return _out(opus, _critique_counts(db, [opus.id]))


@router.post("/api/opuses", response_model=OpusOut, status_code=status.HTTP_201_CREATED)
def create_opus(data: OpusCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    values = data.model_dump(exclude={"markers", "measure_markers"}, exclude_none=True)
    values.setdefault("audio_type", "none")
    values.setdefault("tags", [])
    _normalize_audio(values)
    _check_files(user, values)
    _check_files(user, values)
    _check_markers(data.markers, data.score_page_count)
    _check_measure_markers(data.measure_markers)
    opus = Opus(
        author_id=user.id, slug=unique_slug(db, Opus.slug, data.title), auto_page_markers=not data.markers, **values,
    )
    _set_markers(db, opus, data.markers)
    _set_measure_markers(db, opus, data.measure_markers)
    _sync_page_markers(db, opus)
    db.add(opus)
    db.commit()
    return _out(opus)


@router.patch("/api/opuses/{slug}", response_model=OpusOut)
def update_opus(slug: str, data: OpusUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opus = _own_opus(db, slug, user)
    values = data.model_dump(exclude={"markers", "measure_markers"}, exclude_unset=True)
    if "audio_type" in values or "audio_source" in values:
        values.setdefault("audio_type", opus.audio_type)
        values.setdefault("audio_source", opus.audio_source)
        _normalize_audio(values)
    _check_files(user, values, opus)
    # Remove replaced files from storage
    if opus.audio_type == "hosted_file" and values.get("audio_source", opus.audio_source) != opus.audio_source:
        delete_own(user, opus.audio_source)
    for key_field in ("score_file_key", "musicxml_file_key"):
        if key_field in values and values[key_field] != getattr(opus, key_field):
            delete_own(user, getattr(opus, key_field))
    if "cover_url" in values and values["cover_url"] != opus.cover_url:
        delete_own(user, storage.key_from_url(opus.cover_url))
    for field, value in values.items():
        setattr(opus, field, value)
    if data.markers is not None:
        opus.auto_page_markers = not data.markers
        _check_markers(data.markers, opus.score_page_count)
        _set_markers(db, opus, data.markers)
    if data.measure_markers is not None:
        _check_measure_markers(data.measure_markers)
        _set_measure_markers(db, opus, data.measure_markers)
    _sync_page_markers(db, opus)
    db.commit()
    return _out(opus, _critique_counts(db, [opus.id]))


@router.delete("/api/opuses/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opus(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    opus = _own_opus(db, slug, user)
    if opus.audio_type == "hosted_file":
        delete_own(user, opus.audio_source)
    delete_own(user, opus.score_file_key)
    delete_own(user, opus.musicxml_file_key)
    delete_own(user, storage.key_from_url(opus.cover_url))
    db.delete(opus)
    db.commit()


@router.put("/api/opuses/{slug}/markers", response_model=list[Marker])
def set_markers(slug: str, markers: list[Marker], user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Replace page-turn markers: page N starts at timestamp_seconds"""
    opus = _own_opus(db, slug, user)
    _check_markers(markers, opus.score_page_count)
    opus.auto_page_markers = not markers
    _set_markers(db, opus, markers)
    _sync_page_markers(db, opus)
    db.commit()
    return opus.markers


@router.put("/api/opuses/{slug}/measure-markers", response_model=list[MeasureMarker])
def set_measure_markers(slug: str, markers: list[MeasureMarker], user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Replace MusicXML cursor markers: measure N starts at timestamp_seconds"""
    opus = _own_opus(db, slug, user)
    _check_measure_markers(markers)
    _set_measure_markers(db, opus, markers)
    _sync_page_markers(db, opus)
    db.commit()
    return opus.measure_markers


@router.post("/api/opuses/{slug}/play", status_code=status.HTTP_204_NO_CONTENT)
def register_play(slug: str, db: Session = Depends(get_db)):
    db.execute(update(Opus).where(Opus.slug == slug).values(play_count=Opus.play_count + 1))
    db.commit()


@router.get("/api/opuses/{slug}/score")
def download_score(slug: str, user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    opus = _get_opus(db, slug, user)
    return _download(opus, opus.score_file_key, user, "application/pdf", ".pdf")


@router.get("/api/opuses/{slug}/musicxml")
def download_musicxml(slug: str, user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    opus = _get_opus(db, slug, user)
    compressed = (opus.musicxml_file_key or "").lower().endswith(".mxl")
    media_type = "application/vnd.recordare.musicxml" if compressed else "application/vnd.recordare.musicxml+xml"
    return _download(opus, opus.musicxml_file_key, user, media_type, ".mxl" if compressed else ".musicxml")


# ---------------------------------------------------------------- collections

def _collection_out(db: Session, collection: Collection, author: User, user: Optional[User]) -> CollectionOut:
    opuses = [item.opus for item in collection.items if _visible(item.opus, user) and item.opus.status != "unlisted"]
    return CollectionOut(
        id=collection.id, slug=collection.slug, title=collection.title, description=collection.description,
        year=collection.year, created_at=collection.created_at, author=author, opuses=_outs(db, opuses),
    )


def _set_items(db: Session, collection: Collection, opus_ids: list[uuid.UUID], user: User) -> None:
    own = set(db.scalars(select(Opus.id).where(Opus.id.in_(opus_ids), Opus.author_id == user.id)))
    if len(own) != len(set(opus_ids)):
        raise HTTPException(422, "В сборник можно добавить только свои опусы")
    collection.items = [
        CollectionItem(opus_id=opus_id, position=i) for i, opus_id in enumerate(dict.fromkeys(opus_ids))
    ]


def _own_collection(db: Session, collection_id: uuid.UUID, user: User) -> Collection:
    collection = db.get(Collection, collection_id)
    if not collection or collection.author_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сборник не найден")
    return collection


@router.get("/api/collections", response_model=list[CollectionOut])
def list_collections(author: str, user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    owner = db.scalar(select(User).where(User.username == author.lower(), User.is_hidden.is_(False)))
    if not owner:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Автор не найден")
    collections = db.scalars(
        select(Collection).where(Collection.author_id == owner.id).order_by(Collection.year.desc(), Collection.created_at.desc())
    ).all()
    return [_collection_out(db, c, owner, user) for c in collections]


@router.post("/api/collections", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
def create_collection(data: CollectionIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    collection = Collection(
        author_id=user.id, title=data.title, description=data.description, year=data.year,
        slug=unique_slug(db, Collection.slug, data.title, Collection.author_id == user.id),
    )
    _set_items(db, collection, data.opus_ids, user)
    db.add(collection)
    db.commit()
    return _collection_out(db, collection, user, user)


@router.patch("/api/collections/{collection_id}", response_model=CollectionOut)
def update_collection(collection_id: uuid.UUID, data: CollectionUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    collection = _own_collection(db, collection_id, user)
    for field in ("title", "description", "year"):
        if field in data.model_fields_set:
            setattr(collection, field, getattr(data, field))
    if data.opus_ids is not None:
        _set_items(db, collection, data.opus_ids, user)
    db.commit()
    db.refresh(collection)
    return _collection_out(db, collection, user, user)


@router.delete("/api/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(collection_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_own_collection(db, collection_id, user))
    db.commit()


# ---------------------------------------------------------------- library & search

@router.get("/api/library/facets", response_model=Facets)
def library_facets(db: Session = Depends(get_db)):
    """Filter values for the library with the number of published works for each"""
    rows = db.execute(
        select(Opus.ensemble, Opus.form, Opus.key_signature, Opus.difficulty, Opus.tags).where(Opus.status == "published", visible_authors(Opus.author_id))
    ).all()
    ens = Counter(r.ensemble for r in rows)
    forms = Counter(r.form for r in rows)
    keys = Counter(r.key_signature for r in rows if r.key_signature)
    diff = Counter(r.difficulty for r in rows if r.difficulty)
    tags = Counter(t for r in rows for t in (r.tags or []))
    return Facets(
        ensembles=[Facet(value=k, label=v, count=ens[k]) for k, v in enums.ENSEMBLES.items()],
        forms=[Facet(value=k, label=v, count=forms[k]) for k, v in enums.FORMS.items()],
        keys=[Facet(value=k, label=k, count=n) for k, n in sorted(keys.items())],
        difficulty=[Facet(value=str(k), label=v, count=diff[k]) for k, v in enums.DIFFICULTY.items()],
        tags=[Facet(value=k, label=k, count=n) for k, n in tags.most_common(30)],
    )


@router.get("/api/search", response_model=SearchResult)
def search(q: str = Query(min_length=1, max_length=100), limit: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """Quick search (Ctrl+K) across composers, opuses, posts and instrument tags"""
    needle = q.strip().lower()
    composers = db.scalars(
        select(User).where(User.is_hidden.is_(False), or_(
            func.lower(User.username).contains(needle, autoescape=True),
            func.lower(User.display_name).contains(needle, autoescape=True),
            func.lower(User.pseudonym).contains(needle, autoescape=True),
        )).limit(limit)
    ).all()
    opuses = db.scalars(
        select(Opus).where(Opus.status == "published", visible_authors(Opus.author_id), or_(
            func.lower(Opus.title).contains(needle, autoescape=True),
            func.lower(Opus.subtitle).contains(needle, autoescape=True),
            func.lower(Opus.instrumentation).contains(needle, autoescape=True),
            func.lower(cast(Opus.tags, String)).contains(needle, autoescape=True),
        )).order_by(Opus.play_count.desc()).limit(limit)
    ).unique().all()
    posts = db.scalars(
        select(Post).where(Post.status == "published", visible_authors(Post.author_id), func.lower(Post.title).contains(needle, autoescape=True))
        .order_by(Post.created_at.desc()).limit(limit)
    ).unique().all()
    all_tags = Counter(
        t for tags in db.scalars(select(Opus.tags).where(Opus.status == "published", visible_authors(Opus.author_id))) for t in (tags or [])
    )
    tags = [t for t, _ in all_tags.most_common() if needle in t][:limit]
    return SearchResult(
        composers=[SearchComposer.model_validate(u) for u in composers],
        opuses=[SearchOpus(slug=o.slug, title=o.title, subtitle=o.subtitle, author=o.author) for o in opuses],
        posts=[SearchPost(slug=p.slug, title=p.title, kind=p.kind, author=p.author) for p in posts],
        tags=tags,
    )
