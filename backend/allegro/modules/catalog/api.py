"""HTTP layer of the catalog module: opuses, score sync markers, collections, library facets, performances"""
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from allegro.core.db import get_db
from allegro.core.errors import Unauthorized
from allegro.modules.accounts.deps import get_current_user, get_optional_user, require
from allegro.modules.accounts.roles import Capability
from allegro.modules.catalog import service
from allegro.modules.catalog.schemas import (
    CollectionIn, CollectionOut, CollectionUpdate, Facets, Marker, MeasureMarker, OpusCreate, OpusOut, OpusPage,
    OpusUpdate, PerformanceFields, PerformanceIn, PerformanceOut, PerformancePage,
)

router = APIRouter(tags=["catalog"])


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
    featured: Optional[bool] = None,
    sort: Literal["new", "popular", "title"] = "new",
    mine: bool = False,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """«Сочинения» on the main page, a composer's library and showcase. `mine=true` includes the caller's drafts."""
    if mine and not user:
        raise Unauthorized("Требуется вход")
    items, total = service.list_opuses(
        db, user, author=author, mine=mine, ensemble=ensemble, form=form, key=key, difficulty=difficulty, tag=tag,
        q=q, featured=featured, sort=sort, limit=limit, offset=offset,
    )
    return OpusPage(items=service.opuses_out(db, items), total=total)


@router.get("/api/opuses/{slug}", response_model=OpusOut)
def get_opus(slug: str, user=Depends(get_optional_user), db: Session = Depends(get_db)):
    return service.opuses_out(db, [service.get_opus(db, slug, user)])[0]


@router.post("/api/opuses", response_model=OpusOut, status_code=status.HTTP_201_CREATED)
def create_opus(data: OpusCreate, user=Depends(require(Capability.PUBLISH_OPUS)), db: Session = Depends(get_db)):
    return service.opus_out(service.create_opus(db, user, data))


@router.patch("/api/opuses/{slug}", response_model=OpusOut)
def update_opus(slug: str, data: OpusUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.opuses_out(db, [service.update_opus(db, user, slug, data)])[0]


@router.delete("/api/opuses/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_opus(slug: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service.delete_opus(db, user, slug)


@router.put("/api/opuses/{slug}/markers", response_model=list[Marker])
def set_markers(slug: str, markers: list[Marker], user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.set_markers(db, user, slug, markers).markers


@router.put("/api/opuses/{slug}/measure-markers", response_model=list[MeasureMarker])
def set_measure_markers(slug: str, markers: list[MeasureMarker], user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.set_measure_markers(db, user, slug, markers).measure_markers


@router.post("/api/opuses/{slug}/play", status_code=status.HTTP_204_NO_CONTENT)
def register_play(slug: str, db: Session = Depends(get_db)):
    service.register_play(db, slug)


def _file_response(chunks, media_type: str, filename: str) -> StreamingResponse:
    return StreamingResponse(chunks, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/api/opuses/{slug}/score")
def download_score(slug: str, user=Depends(get_optional_user), db: Session = Depends(get_db)):
    opus = service.get_opus(db, slug, user)
    return _file_response(service.download(opus, opus.score_file_key, user), "application/pdf", f"{opus.slug}.pdf")


@router.get("/api/opuses/{slug}/musicxml")
def download_musicxml(slug: str, user=Depends(get_optional_user), db: Session = Depends(get_db)):
    opus = service.get_opus(db, slug, user)
    compressed = (opus.musicxml_file_key or "").lower().endswith(".mxl")
    media_type = "application/vnd.recordare.musicxml" if compressed else "application/vnd.recordare.musicxml+xml"
    return _file_response(service.download(opus, opus.musicxml_file_key, user), media_type,
                          f"{opus.slug}{'.mxl' if compressed else '.musicxml'}")


# ---------------------------------------------------------------- collections

@router.get("/api/collections", response_model=list[CollectionOut])
def list_collections(author: str, user=Depends(get_optional_user), db: Session = Depends(get_db)):
    owner, collections = service.list_collections(db, author)
    return [service.collection_out(db, c, owner, user) for c in collections]


@router.post("/api/collections", response_model=CollectionOut, status_code=status.HTTP_201_CREATED)
def create_collection(data: CollectionIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.collection_out(db, service.create_collection(db, user, data), user, user)


@router.patch("/api/collections/{collection_id}", response_model=CollectionOut)
def update_collection(collection_id: uuid.UUID, data: CollectionUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.collection_out(db, service.update_collection(db, user, collection_id, data), user, user)


@router.delete("/api/collections/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_collection(collection_id: uuid.UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service.delete_collection(db, user, collection_id)


# ---------------------------------------------------------------- library

@router.get("/api/library/facets", response_model=Facets)
def library_facets(author: Optional[str] = None, db: Session = Depends(get_db)):
    """Filter values for the library — all works, or one composer's — with the number of works for each"""
    return service.facets(db, author)


# ---------------------------------------------------------------- performances

@router.get("/api/performances", response_model=PerformancePage)
def list_performances(
    performer: Optional[str] = None,
    opus: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """«Исполнения»: all members', one performer's, or of one work"""
    items, total = service.list_performances(db, user, performer=performer, opus=opus, limit=limit, offset=offset)
    return PerformancePage(items=[service.performance_out(p) for p in items], total=total)


@router.post("/api/performances", response_model=PerformanceOut, status_code=status.HTTP_201_CREATED)
def create_performance(data: PerformanceIn, user=Depends(require(Capability.PUBLISH_PERFORMANCE)), db: Session = Depends(get_db)):
    return service.performance_out(service.create_performance(db, user, data))


@router.patch("/api/performances/{performance_id}", response_model=PerformanceOut)
def update_performance(performance_id: uuid.UUID, data: PerformanceFields, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.performance_out(service.update_performance(db, user, performance_id, data))


@router.delete("/api/performances/{performance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_performance(performance_id: uuid.UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service.delete_performance(db, user, performance_id)


@router.post("/api/performances/{performance_id}/play", status_code=status.HTTP_204_NO_CONTENT)
def register_performance_play(performance_id: uuid.UUID, db: Session = Depends(get_db)):
    service.register_performance_play(db, performance_id)
