"""HTTP layer of the media module: uploads (files are served by the storage itself, see allegro.main)"""
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from allegro.core.db import get_db
from allegro.modules.accounts.deps import get_current_user
from allegro.modules.media import service
from allegro.modules.media.schemas import Uploaded

router = APIRouter(tags=["media"])

Purpose = Literal["score", "musicxml", "audio", "image", "cover", "attachment"]


@router.post("/api/media", response_model=list[Uploaded], status_code=status.HTTP_201_CREATED)
async def upload(
    files: list[UploadFile] = File(...),
    purpose: Purpose = Form("attachment"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await service.save_uploads(db, files, purpose, user)
