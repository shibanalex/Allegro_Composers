"""Use cases of the catalog module: works (opuses) with score sync, collections, the library, performances.

Public API for other modules: `opus_brief`, `opus_id_by_slug`, `resolve_opus_target`, `visible_published_opus`,
`search_opuses`, `popular_tags`, `count_opuses`, `count_performances`.
"""
import uuid
from collections import Counter
from typing import Iterator, Optional

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from allegro.core.errors import Forbidden, Invalid, NotFound
from allegro.core.files import check_key, check_url, delete_own_after_commit, delete_own_url_after_commit
from allegro.core.slugs import unique_slug
from allegro.core.storage import storage
from allegro.core import textsearch
from allegro.modules.accounts.service import get_visible_user, visible_authors
from allegro.modules.catalog import enums, repository as repo
from allegro.modules.catalog.models import (
    Collection, CollectionItem, MeasureSyncMarker, Opus, Performance, ScoreSyncMarker,
)
from allegro.modules.catalog.musicxml import page_start_times
from allegro.modules.catalog.schemas import (
    YOUTUBE_ID, CollectionIn, CollectionOut, CollectionUpdate, Facet, Facets, Marker, MeasureMarker, OpusBrief,
    OpusCreate, OpusOut, OpusUpdate, PerformanceFields, PerformanceIn, PerformanceOut,
)
from allegro.modules.discussion.service import Target, count_comments


# ---------------------------------------------------------------- shaping answers

def opus_out(opus: Opus, counts: Optional[dict] = None) -> OpusOut:
    out = OpusOut.model_validate(opus)
    return out.model_copy(update={
        "audio_url": storage.url(opus.audio_source) if opus.audio_type == "hosted_file" else None,
        "score_url": storage.url(opus.score_file_key),
        "musicxml_url": storage.url(opus.musicxml_file_key),
        "critique_count": (counts or {}).get(opus.id, 0),
    })


def opuses_out(db: Session, opuses: list[Opus]) -> list[OpusOut]:
    counts = count_comments(db, "opus", [o.id for o in opuses])
    return [opus_out(o, counts) for o in opuses]


def opus_brief(opus: Optional[Opus]) -> Optional[OpusBrief]:
    """An opus as other modules show it; None for drafts and works of shadowed authors"""
    if not opus or opus.status == "draft" or opus.author.is_hidden:
        return None
    brief = OpusBrief.model_validate(opus)
    return brief.model_copy(update={"audio_url": storage.url(opus.audio_source) if opus.audio_type == "hosted_file" else None})


# ---------------------------------------------------------------- visibility

def _visible(opus: Optional[Opus], user) -> bool:
    if not opus or opus.author.is_hidden:  # works of shadowed accounts vanish from the site
        return False
    return opus.status != "draft" or (user is not None and user.id == opus.author_id)


def get_opus(db: Session, slug: str, user) -> Opus:
    opus = repo.opus_by_slug(db, slug)
    if not _visible(opus, user):
        raise NotFound("Опус не найден")
    return opus


def _own_opus(db: Session, slug: str, user) -> Opus:
    opus = get_opus(db, slug, user)
    if opus.author_id != user.id:
        raise Forbidden("Это не ваш опус")
    return opus


def visible_published_opus(db: Session, opus_id: Optional[uuid.UUID]) -> Optional[Opus]:
    """A work others may refer to (a workshop thread, a performance)"""
    if not opus_id:
        return None
    opus = db.get(Opus, opus_id)
    if not opus or opus.status == "draft" or opus.author.is_hidden:
        raise Invalid("Опус не найден")
    return opus


def opus_id_by_slug(db: Session, slug: str) -> Optional[uuid.UUID]:
    opus = repo.opus_by_slug(db, slug)
    return opus.id if opus else None


def resolve_opus_target(db: Session, opus_id: uuid.UUID, user) -> Optional[Target]:
    """Comments on an opus (registered with the discussion module)"""
    opus = db.get(Opus, opus_id)
    if not _visible(opus, user):
        return None
    return Target(owner_id=opus.author_id, has_recording=True)


# ---------------------------------------------------------------- audio, files, markers

def _normalize_audio(values: dict) -> None:
    """Validate audio fields in-place; accepts a full YouTube URL and stores only the video id"""
    audio_type = values.get("audio_type")
    source = (values.get("audio_source") or "").strip() or None
    if audio_type == "youtube":
        match = YOUTUBE_ID.search(source or "")
        video_id = match.group(1) if match else source
        if not video_id or len(video_id) != 11:
            raise Invalid("Укажите ссылку на YouTube или id видео")
        values["audio_source"] = video_id
    elif audio_type == "hosted_file":
        if not source:
            raise Invalid("Загрузите аудиофайл")
        values["audio_source"] = source
    elif audio_type == "none":
        values["audio_source"] = None


def _check_files(user, values: dict, opus: Optional[Opus] = None) -> None:
    """Score, MusicXML, audio and cover must be the author's own uploads (or already on this opus)"""
    for field in ("score_file_key", "musicxml_file_key"):
        if field in values:
            check_key(user.username, values[field], [getattr(opus, field, None)])
    if values.get("audio_type") == "hosted_file":
        check_key(user.username, values.get("audio_source"), [getattr(opus, "audio_source", None)])
    if "cover_url" in values:
        check_url(user.username, values["cover_url"], [getattr(opus, "cover_url", None)])


def _check_markers(markers: list[Marker], page_count: Optional[int]) -> None:
    pages = [m.page_number for m in markers]
    if len(pages) != len(set(pages)):
        raise Invalid("У каждой страницы может быть только одна отметка")
    if page_count and any(p > page_count for p in pages):
        raise Invalid(f"В партитуре всего {page_count} стр.")


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
        raise Invalid("У каждого такта может быть только одна отметка")
    if any(b.timestamp_seconds <= a.timestamp_seconds for a, b in zip(ordered, ordered[1:])):
        raise Invalid("Отметки тактов должны идти по возрастанию времени")


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


# ---------------------------------------------------------------- opuses

def list_opuses(db: Session, user, *, author=None, mine=False, **filters) -> tuple[list[Opus], int]:
    """Feed «Сочинения», the library and the hall. `mine` includes the caller's drafts."""
    return repo.opus_page(db, author_username=author, owner_id=user.id if mine else None, **filters)


def create_opus(db: Session, user, data: OpusCreate) -> Opus:
    values = data.model_dump(exclude={"markers", "measure_markers"}, exclude_none=True)
    values.setdefault("audio_type", "none")
    values.setdefault("tags", [])
    _normalize_audio(values)
    _check_files(user, values)
    _check_markers(data.markers, data.score_page_count)
    _check_measure_markers(data.measure_markers)
    opus = Opus(author_id=user.id, slug=unique_slug(db, Opus.slug, data.title), auto_page_markers=not data.markers, **values)
    _set_markers(db, opus, data.markers)
    _set_measure_markers(db, opus, data.measure_markers)
    _sync_page_markers(db, opus)
    db.add(opus)
    db.commit()
    return opus


def update_opus(db: Session, user, slug: str, data: OpusUpdate) -> Opus:
    opus = _own_opus(db, slug, user)
    values = data.model_dump(exclude={"markers", "measure_markers"}, exclude_unset=True)
    if "audio_type" in values or "audio_source" in values:
        values.setdefault("audio_type", opus.audio_type)
        values.setdefault("audio_source", opus.audio_source)
        _normalize_audio(values)
    _check_files(user, values, opus)
    # Remove replaced files from storage, once the change is saved
    if opus.audio_type == "hosted_file" and values.get("audio_source", opus.audio_source) != opus.audio_source:
        delete_own_after_commit(db, user.username, opus.audio_source)
    for key_field in ("score_file_key", "musicxml_file_key"):
        if key_field in values and values[key_field] != getattr(opus, key_field):
            delete_own_after_commit(db, user.username, getattr(opus, key_field))
    if "cover_url" in values and values["cover_url"] != opus.cover_url:
        delete_own_url_after_commit(db, user.username, opus.cover_url)
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
    return opus


def delete_opus(db: Session, user, slug: str) -> None:
    opus = _own_opus(db, slug, user)
    if opus.audio_type == "hosted_file":
        delete_own_after_commit(db, user.username, opus.audio_source)
    delete_own_after_commit(db, user.username, opus.score_file_key)
    delete_own_after_commit(db, user.username, opus.musicxml_file_key)
    delete_own_url_after_commit(db, user.username, opus.cover_url)
    db.delete(opus)
    db.commit()


def set_markers(db: Session, user, slug: str, markers: list[Marker]) -> Opus:
    """Replace page-turn markers: page N starts at timestamp_seconds"""
    opus = _own_opus(db, slug, user)
    _check_markers(markers, opus.score_page_count)
    opus.auto_page_markers = not markers
    _set_markers(db, opus, markers)
    _sync_page_markers(db, opus)
    db.commit()
    return opus


def set_measure_markers(db: Session, user, slug: str, markers: list[MeasureMarker]) -> Opus:
    """Replace MusicXML cursor markers: measure N starts at timestamp_seconds"""
    opus = _own_opus(db, slug, user)
    _check_measure_markers(markers)
    _set_measure_markers(db, opus, markers)
    _sync_page_markers(db, opus)
    db.commit()
    return opus


def register_play(db: Session, slug: str) -> None:
    db.execute(update(Opus).where(Opus.slug == slug).values(play_count=Opus.play_count + 1))
    db.commit()


def download(opus: Opus, key: Optional[str], user) -> Iterator[bytes]:
    """Score files honour the author's choice: free / view only / paid"""
    if not key:
        raise NotFound("Файла нет")
    is_author = user is not None and user.id == opus.author_id
    if opus.score_access != "free" and not is_author:
        detail = "Партитура доступна только для просмотра" if opus.score_access == "view_only" else "Скачивание за донат появится позже"
        raise Forbidden(detail)
    chunks = storage.open_stream(key)
    if chunks is None:
        raise NotFound("Файл не найден")
    return chunks


# ---------------------------------------------------------------- collections

def collection_out(db: Session, collection: Collection, author, user) -> CollectionOut:
    opuses = [item.opus for item in collection.items if _visible(item.opus, user) and item.opus.status != "unlisted"]
    return CollectionOut(
        id=collection.id, slug=collection.slug, title=collection.title, description=collection.description,
        year=collection.year, created_at=collection.created_at, author=author, opuses=opuses_out(db, opuses),
    )


def list_collections(db: Session, author_username: str):
    owner = get_visible_user(db, author_username)
    if not owner:
        raise NotFound("Автор не найден")
    return owner, repo.collections_of(db, owner.id)


def _set_items(db: Session, collection: Collection, opus_ids: list[uuid.UUID], user) -> None:
    own = repo.own_opus_ids(db, user.id, opus_ids)
    if len(own) != len(set(opus_ids)):
        raise Invalid("В сборник можно добавить только свои опусы")
    collection.items = [
        CollectionItem(opus_id=opus_id, position=i) for i, opus_id in enumerate(dict.fromkeys(opus_ids))
    ]


def _own_collection(db: Session, collection_id: uuid.UUID, user) -> Collection:
    collection = db.get(Collection, collection_id)
    if not collection or collection.author_id != user.id:
        raise NotFound("Сборник не найден")
    return collection


def create_collection(db: Session, user, data: CollectionIn) -> Collection:
    collection = Collection(
        author_id=user.id, title=data.title, description=data.description, year=data.year,
        slug=unique_slug(db, Collection.slug, data.title, Collection.author_id == user.id),
    )
    _set_items(db, collection, data.opus_ids, user)
    db.add(collection)
    db.commit()
    return collection


def update_collection(db: Session, user, collection_id: uuid.UUID, data: CollectionUpdate) -> Collection:
    collection = _own_collection(db, collection_id, user)
    for field in ("title", "description", "year"):
        if field in data.model_fields_set:
            setattr(collection, field, getattr(data, field))
    if data.opus_ids is not None:
        _set_items(db, collection, data.opus_ids, user)
    db.commit()
    db.refresh(collection)
    return collection


def delete_collection(db: Session, user, collection_id: uuid.UUID) -> None:
    db.delete(_own_collection(db, collection_id, user))
    db.commit()


# ---------------------------------------------------------------- library facets

def facets(db: Session, author_username: Optional[str] = None) -> Facets:
    """Filter values for the library (all works, or one composer's) with the number of works for each"""
    author_id = None
    if author_username:
        owner = get_visible_user(db, author_username)
        if not owner:
            raise NotFound("Автор не найден")
        author_id = owner.id
    rows = repo.facet_rows(db, author_id)
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


# ---------------------------------------------------------------- performances

def performance_out(performance: Performance) -> PerformanceOut:
    out = PerformanceOut.model_validate(performance)
    return out.model_copy(update={
        "opus": opus_brief(performance.opus),
        "audio_url": storage.url(performance.audio_source) if performance.audio_type == "hosted_file" else None,
    })


def list_performances(db: Session, user, *, performer: Optional[str] = None, opus: Optional[str] = None,
                      limit: int = 20, offset: int = 0) -> tuple[list[Performance], int]:
    performer_id = opus_id = None
    if performer:
        owner = get_visible_user(db, performer)
        if not owner:
            return [], 0
        performer_id = owner.id
    if opus:
        target = repo.opus_by_slug(db, opus)
        if not _visible(target, user):
            return [], 0
        opus_id = target.id
    return repo.performance_page(
        db, performer_id=performer_id, opus_id=opus_id, include_drafts_of=user.id if user else None, limit=limit, offset=offset,
    )


def _own_performance(db: Session, performance_id: uuid.UUID, user) -> Performance:
    performance = db.get(Performance, performance_id)
    if not performance or performance.performer_id != user.id:
        raise NotFound("Исполнение не найдено")
    return performance


def _performance_values(user, values: dict, performance: Optional[Performance] = None) -> dict:
    if "audio_type" in values or "audio_source" in values:
        values.setdefault("audio_type", performance.audio_type if performance else None)
        values.setdefault("audio_source", performance.audio_source if performance else None)
        _normalize_audio(values)
        if values["audio_type"] == "hosted_file":
            check_key(user.username, values["audio_source"], [performance.audio_source if performance else None])
    return values


def create_performance(db: Session, user, data: PerformanceIn) -> Performance:
    values = _performance_values(user, data.model_dump(exclude_none=True))
    visible_published_opus(db, data.opus_id)
    performance = Performance(performer_id=user.id, **values)
    db.add(performance)
    db.commit()
    db.refresh(performance)
    return performance


def update_performance(db: Session, user, performance_id: uuid.UUID, data: PerformanceFields) -> Performance:
    performance = _own_performance(db, performance_id, user)
    values = _performance_values(user, data.model_dump(exclude_unset=True), performance)
    if "opus_id" in values:
        visible_published_opus(db, values["opus_id"])
    if performance.audio_type == "hosted_file" and values.get("audio_source", performance.audio_source) != performance.audio_source:
        delete_own_after_commit(db, user.username, performance.audio_source)
    for field, value in values.items():
        setattr(performance, field, value)
    db.commit()
    db.refresh(performance)
    return performance


def delete_performance(db: Session, user, performance_id: uuid.UUID) -> None:
    performance = _own_performance(db, performance_id, user)
    if performance.audio_type == "hosted_file":
        delete_own_after_commit(db, user.username, performance.audio_source)
    db.delete(performance)
    db.commit()


def register_performance_play(db: Session, performance_id: uuid.UUID) -> None:
    db.execute(update(Performance).where(Performance.id == performance_id).values(play_count=Performance.play_count + 1))
    db.commit()


# ---------------------------------------------------------------- for other modules

def count_opuses(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    return repo.count_by(db, Opus.author_id, user_ids, Opus.status == "published")


def count_performances(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    return repo.count_by(db, Performance.performer_id, user_ids, Performance.status == "published")


def search_opuses(db: Session, words: list[str], limit: int) -> list[Opus]:
    from sqlalchemy import String, cast

    return list(db.scalars(
        select(Opus).where(
            Opus.status == "published", visible_authors(Opus.author_id),
            textsearch.matches_all([
                Opus.title, Opus.subtitle, Opus.instrumentation, Opus.key_signature,
                cast(Opus.tags, String), Opus.description_md,
            ], words),
        ).order_by(Opus.play_count.desc(), Opus.created_at.desc()).limit(limit)
    ).unique())


def popular_tags(db: Session) -> list[str]:
    all_tags = Counter(
        t for tags in db.scalars(select(Opus.tags).where(Opus.status == "published", visible_authors(Opus.author_id)))
        for t in (tags or [])
    )
    return [t for t, _ in all_tags.most_common()]
