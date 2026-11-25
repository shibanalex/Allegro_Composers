"""Uploads to storage (scores, MusicXML, audio, images, covers, attachments): what may be uploaded, checked by content"""
from pathlib import Path
from typing import Literal

from datetime import datetime, timedelta, timezone

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from allegro.core import images, peaks
from allegro.core.config import settings
from allegro.core.errors import Invalid, PayloadTooLarge, UnsupportedMedia
from allegro.core.storage import UploadTooLarge, content_type_for, storage
from allegro.modules.accounts.roles import Capability, can
from allegro.modules.media.models import Upload

# "cover": a picture cropped to a square (covers of works, like album covers)
Purpose = Literal["score", "musicxml", "audio", "image", "cover", "attachment"]

# Accepted file extensions per purpose. The extension decides how the file is served later, so it is
# checked instead of the MIME type the browser claims (which the uploader controls).
ALLOWED = {
    "score": {".pdf"},
    "audio": {".mp3", ".wav", ".ogg", ".oga", ".opus", ".flac", ".m4a", ".aac", ".webm"},
    # no SVG: it may carry scripts
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif"},
}
ALLOWED["cover"] = ALLOWED["image"]
# Attachments: what musicians share; notation files, MIDI, texts, tables, books, archives, pictures, audio.
# A list of what is allowed, not of what is forbidden: no programs, pages or scripts can slip in.
ATTACHMENTS = {
    ".pdf", ".mid", ".midi", ".kar", ".musicxml", ".xml", ".mxl", ".mscz", ".mscx", ".sib", ".mus", ".musx",
    ".dorico", ".ly", ".gp", ".gp3", ".gp4", ".gp5", ".gpx", ".ptb", ".txt", ".md", ".rtf", ".doc", ".docx",
    ".odt", ".xls", ".xlsx", ".ods", ".ppt", ".pptx", ".odp", ".epub", ".fb2", ".djvu", ".zip", ".7z", ".rar",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif",
    ".mp3", ".wav", ".ogg", ".oga", ".opus", ".flac", ".m4a", ".aac", ".webm",
}
MAX_FILES = 10  # in one request
# The largest file of each kind, in MB (MAX_UPLOAD_MB caps them all); the site checks the same before uploading
LIMIT_MB = {"score": 50, "musicxml": 20, "audio": 100, "image": 30, "cover": 30, "attachment": 50}
MB = 1024 * 1024

MUSICXML_EXTENSIONS = {".musicxml", ".xml", ".mxl"}


async def _check_musicxml(file: UploadFile) -> None:
    """Browsers send random MIME types for MusicXML, so check the extension and the content instead"""
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in MUSICXML_EXTENSIONS:
        raise UnsupportedMedia(f"Нужен файл MusicXML (.musicxml, .xml или .mxl): {file.filename}")
    head = await file.read(4096)
    await file.seek(0)
    if suffix == ".mxl":
        ok = head.startswith(b"PK")  # compressed MusicXML is a ZIP container
    else:
        ok = b"score-partwise" in head or b"score-timewise" in head
    if not ok:
        raise UnsupportedMedia(f"Файл не похож на MusicXML: {file.filename}")


async def _save_picture(file: UploadFile, purpose: str, username: str) -> dict:
    """Decode the picture (a file that only pretends to be one is refused), crop a cover to a square,
    store it with its light preview"""
    spool, _ = await storage.spool(file, _limit(purpose))
    with spool:
        data = spool.read()
    try:
        done = await run_in_threadpool(images.process, data, purpose == "cover")
    except images.NotAnImage:
        raise UnsupportedMedia(f"Файл не похож на изображение: {file.filename}")
    name = file.filename or "image"
    if done.extension:
        name = Path(name).stem + done.extension
    key = storage.new_key(f"{purpose}s/{username}", name)
    body = done.original or data
    await run_in_threadpool(storage.save_bytes, key, body)
    preview_url = None
    if done.preview:
        preview_url = await run_in_threadpool(storage.save_bytes, images.preview_key(key), done.preview)
    return {
        "key": key, "url": storage.url(key), "name": file.filename or name,
        "content_type": content_type_for(key), "size": len(body), "preview_url": preview_url,
    }


def _limit(purpose: str) -> int:
    return min(LIMIT_MB.get(purpose, 50), settings.max_upload_mb)


def limits() -> dict[str, int]:
    return {purpose: _limit(purpose) for purpose in LIMIT_MB}


def _uploaded_today(db: Session, user) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=1)
    return db.scalar(select(func.coalesce(func.sum(Upload.size), 0)).where(Upload.user_id == user.id, Upload.created_at >= since)) or 0


async def _forget_file(key: str) -> None:
    await run_in_threadpool(storage.delete, key)
    if images.is_picture(key):
        await run_in_threadpool(storage.delete, images.preview_key(key))
    if peaks.is_audio(key):
        await run_in_threadpool(storage.delete, peaks.peaks_key(key))


async def save_uploads(db: Session, files: list[UploadFile], purpose: str, user) -> list[dict]:
    """Check each file by its extension and content, store it, and count it against the member's daily limit"""
    if len(files) > MAX_FILES:
        raise Invalid(f"За один раз — не больше {MAX_FILES} файлов")
    limited = not can(user, Capability.MANAGE_SITE)
    quota = settings.upload_daily_mb * MB
    used = _uploaded_today(db, user) if limited else 0
    if limited and used >= quota:
        raise PayloadTooLarge(f"На сегодня лимит загрузок исчерпан ({settings.upload_daily_mb} МБ в сутки)")
    saved = []
    for file in files:
        saved.append(await _save_one(file, purpose, user.username))
        size = saved[-1]["size"]
        if limited and used + size > quota:
            for item in saved:  # nothing of this request is kept
                await _forget_file(item["key"])
            left = max(0, quota - used) // MB
            raise PayloadTooLarge(f"Лимит загрузок — {settings.upload_daily_mb} МБ в сутки; сегодня осталось {left} МБ")
        used += size
    db.add_all(Upload(key=item["key"], user_id=user.id, size=item["size"]) for item in saved)
    db.commit()
    return saved


async def _save_one(file: UploadFile, purpose: str, username: str) -> dict:
    suffix = Path(file.filename or "").suffix.lower()
    if purpose == "musicxml":
        await _check_musicxml(file)
    elif purpose == "attachment":
        if suffix not in ATTACHMENTS:
            raise UnsupportedMedia(f"Такой файл прикрепить нельзя: {file.filename}. Подходят ноты (PDF, MusicXML, MIDI, "
                                   "Sibelius, MuseScore…), тексты, таблицы, книги, архивы, картинки и аудио")
    elif suffix not in ALLOWED[purpose]:
        raise UnsupportedMedia(f"Неподходящий тип файла для «{purpose}» ({', '.join(sorted(ALLOWED[purpose]))}): {file.filename}")
    if purpose == "score":
        head = await file.read(5)
        await file.seek(0)
        if head != b"%PDF-":
            raise UnsupportedMedia(f"Файл не похож на PDF: {file.filename}")
    try:
        if purpose in ("image", "cover"):
            return await _save_picture(file, purpose, username)
        # Every upload goes to the uploader's own folder: that is what proves ownership later (core.files)
        item = await storage.save_upload(file, f"{purpose}s/{username}", _limit(purpose))
        # .webm/.mp4 are «video» by their extension; a voice note recorded in the browser is audio
        if purpose == "audio" and item["content_type"].startswith("video/"):
            item["content_type"] = "audio/" + item["content_type"].split("/", 1)[1]
        return item
    except UploadTooLarge as e:
        raise PayloadTooLarge(str(e))
