"""HTTP layer of the media module: uploads (files are served by the storage itself, see allegro.main)"""
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from allegro.core import peaks
from allegro.core.db import get_db
from allegro.core.errors import NotFound
from allegro.core.storage import storage
from allegro.modules.accounts.deps import get_current_user
from allegro.modules.media import service
from allegro.modules.media.schemas import Uploaded

router = APIRouter(tags=["media"])

Purpose = Literal["score", "musicxml", "audio", "image", "cover", "attachment"]


@router.get("/api/media/limits")
def limits():
    """The largest file of each kind, in MB (the upload form checks it before sending)"""
    return service.limits()


@router.post("/api/media", response_model=list[Uploaded], status_code=status.HTTP_201_CREATED)
async def upload(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    purpose: Purpose = Form("attachment"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    saved = await service.save_uploads(db, files, purpose, user)
    # A recording's waveform is drawn after the answer: the upload doesn't wait for the decoding
    for item in saved:
        if peaks.is_audio(item["key"]):
            background.add_task(peaks.make_quietly, item["key"])
    return saved


@router.get("/api/media/peaks")
def waveform(response: Response, url: str = Query(max_length=1000)):
    """The waveform of an uploaded recording, by its address: {duration, peaks: [0..1, ...]}"""
    key = storage.key_from_url(url)
    data = peaks.read(key) if key else None
    if not data:
        raise NotFound("Волна для этой записи ещё не готова")
    response.headers["Cache-Control"] = "public, max-age=86400"
    return data
