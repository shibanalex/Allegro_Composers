"""Uploads to storage (scores, MusicXML, audio, images, covers, attachments): what may be uploaded, checked by content"""
from pathlib import Path
from typing import Literal

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from allegro.core import images
from allegro.core.errors import PayloadTooLarge, UnsupportedMedia
from allegro.core.storage import UploadTooLarge, content_type_for, storage

# "cover": a picture cropped to a square (covers of works, like album covers)
Purpose = Literal["score", "musicxml", "audio", "image", "cover", "attachment"]
PICTURE_LIMIT_MB = 30

# Accepted file extensions per purpose. The extension decides how the file is served later, so it is
# checked instead of the MIME type the browser claims (which the uploader controls).
ALLOWED = {
    "score": {".pdf"},
    "audio": {".mp3", ".wav", ".ogg", ".oga", ".opus", ".flac", ".m4a", ".aac", ".webm"},
    # no SVG: it may carry scripts
    "image": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif"},
}
ALLOWED["cover"] = ALLOWED["image"]
# Attachments may be anything (MIDI, archives, Sibelius files...) except what a browser would run as a page
FORBIDDEN_ATTACHMENTS = {
    ".html", ".htm", ".xhtml", ".xht", ".shtml", ".svg", ".svgz", ".js", ".mjs", ".xsl", ".xslt", ".swf",
}

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
    spool, _ = await storage.spool(file, PICTURE_LIMIT_MB)
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


async def save_uploads(files: list[UploadFile], purpose: str, username: str) -> list[dict]:
    saved = []
    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        if purpose == "musicxml":
            await _check_musicxml(file)
        elif purpose == "attachment":
            if suffix in FORBIDDEN_ATTACHMENTS:
                raise UnsupportedMedia(f"Такие файлы прикреплять нельзя: {file.filename}")
        elif suffix not in ALLOWED[purpose]:
            raise UnsupportedMedia(f"Неподходящий тип файла для «{purpose}» ({', '.join(sorted(ALLOWED[purpose]))}): {file.filename}")
        if purpose == "score":
            head = await file.read(5)
            await file.seek(0)
            if head != b"%PDF-":
                raise UnsupportedMedia(f"Файл не похож на PDF: {file.filename}")
        try:
            if purpose in ("image", "cover"):
                saved.append(await _save_picture(file, purpose, username))
                continue
            # Every upload goes to the uploader's own folder: that is what proves ownership later (core.files)
            saved.append(await storage.save_upload(file, f"{purpose}s/{username}"))
        except UploadTooLarge as e:
            raise PayloadTooLarge(str(e))
    return saved
