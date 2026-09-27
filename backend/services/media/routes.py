"""Media service: uploads to storage (scores, audio, images, attachments); files are served under /media"""
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel

from allegro_common.deps import get_current_user
from allegro_common.models import User
from allegro_common.storage import UploadTooLarge, storage

router = APIRouter(tags=["media"])

Purpose = Literal["score", "musicxml", "audio", "image", "attachment"]

# Accepted file extensions per purpose. The extension decides how the file is served later, so it is
# checked instead of the MIME type the browser claims (which the uploader controls).
ALLOWED = {
    "score": {".pdf"},
    "audio": {".mp3", ".wav", ".ogg", ".oga", ".opus", ".flac", ".m4a", ".aac", ".webm"},
    # no SVG: it may carry scripts
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif"},
}
# Attachments may be anything (MIDI, archives, Sibelius files...) except what a browser would run as a page
FORBIDDEN_ATTACHMENTS = {
    ".html", ".htm", ".xhtml", ".xht", ".shtml", ".svg", ".svgz", ".js", ".mjs", ".xsl", ".xslt", ".swf",
}

MUSICXML_EXTENSIONS = {".musicxml", ".xml", ".mxl"}


class Uploaded(BaseModel):
    key: str
    url: str
    name: str
    content_type: str
    size: int


async def _check_musicxml(file: UploadFile) -> None:
    """Browsers send random MIME types for MusicXML, so check the extension and the content instead"""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in MUSICXML_EXTENSIONS:
        raise HTTPException(415, f"Нужен файл MusicXML (.musicxml, .xml или .mxl): {file.filename}")
    head = await file.read(4096)
    await file.seek(0)
    if suffix == ".mxl":
        ok = head.startswith(b"PK")  # compressed MusicXML is a ZIP container
    else:
        ok = b"score-partwise" in head or b"score-timewise" in head
    if not ok:
        raise HTTPException(415, f"Файл не похож на MusicXML: {file.filename}")


@router.post("/api/media", response_model=list[Uploaded], status_code=status.HTTP_201_CREATED)
async def upload(
    files: list[UploadFile] = File(...),
    purpose: Purpose = Form("attachment"),
    user: User = Depends(get_current_user),
):
    saved = []
    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        if purpose == "musicxml":
            await _check_musicxml(file)
        elif purpose == "attachment":
            if suffix in FORBIDDEN_ATTACHMENTS:
                raise HTTPException(415, f"Такие файлы прикреплять нельзя: {file.filename}")
        elif suffix not in ALLOWED[purpose]:
            raise HTTPException(415, f"Неподходящий тип файла для «{purpose}» ({', '.join(sorted(ALLOWED[purpose]))}): {file.filename}")
        if purpose == "score":
            head = await file.read(5)
            await file.seek(0)
            if head != b"%PDF-":
                raise HTTPException(415, f"Файл не похож на PDF: {file.filename}")
        try:
            saved.append(await storage.save_upload(file, f"{purpose}s/{user.username}"))
        except UploadTooLarge as e:
            raise HTTPException(413, str(e))
    return saved
