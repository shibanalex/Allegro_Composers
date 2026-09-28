"""Uploaded pictures: checked by decoding, square covers, and a light preview next to every picture.

A phone photo is several megabytes; a card in the feed needs a few dozen kilobytes. So every picture
gets a WebP copy no larger than PREVIEW_SIZE, stored beside the original under `<key>.preview.webp`.
The site shows the preview in lists and cards and the original only when the picture is opened.
The name is derived from the original's key, so nothing extra is stored in the database, and the
preview lies in the same owner's folder (core.files).
"""
import io
from dataclasses import dataclass
from typing import Optional

from PIL import Image, ImageOps, UnidentifiedImageError

PREVIEW_SUFFIX = ".preview.webp"
PREVIEW_SIZE = 800  # px, the longer side: sharp on a phone screen at the width of the feed
COVER_SIZE = 1600  # px, the side of a square cover
# Folders whose files are pictures with previews (uploads with purpose "image" and "cover")
PICTURE_FOLDERS = ("images/", "covers/")

# A "decompression bomb" (a tiny file that unpacks into gigapixels) is refused before it is decoded
Image.MAX_IMAGE_PIXELS = 40_000_000


class NotAnImage(ValueError):
    pass


@dataclass
class Processed:
    original: Optional[bytes]  # None: keep the uploaded file as it is
    extension: Optional[str]  # the new extension when the original was re-encoded
    preview: Optional[bytes]  # None: no preview (an animated GIF stays as it is)


def is_picture(key: Optional[str]) -> bool:
    return bool(key) and key.startswith(PICTURE_FOLDERS) and not key.endswith(PREVIEW_SUFFIX)


def preview_key(key: str) -> str:
    return key + PREVIEW_SUFFIX


def _open(data: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(data))  # reads only the header
        if image.width * image.height > Image.MAX_IMAGE_PIXELS:  # Pillow itself would only warn up to 2×
            raise NotAnImage("Слишком большое изображение")
        image.load()
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as e:
        raise NotAnImage(str(e)) from e
    return image


def _webp(image: Image.Image, quality: int) -> bytes:
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() or "transparency" in image.info else "RGB")
    out = io.BytesIO()
    image.save(out, "WEBP", quality=quality, method=4)
    return out.getvalue()


def make_preview(data: bytes) -> Optional[bytes]:
    image = _open(data)
    if getattr(image, "is_animated", False):
        return None
    image = ImageOps.exif_transpose(image)
    image.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE), Image.Resampling.LANCZOS)
    return _webp(image, 80)


def process(data: bytes, square: bool = False) -> Processed:
    """Check that the upload really is a picture; crop covers to a centred square; make the preview"""
    image = _open(data)
    if getattr(image, "is_animated", False):
        return Processed(original=None, extension=None, preview=None)
    image = ImageOps.exif_transpose(image)
    if not square:
        return Processed(original=None, extension=None, preview=make_preview(data))
    side = min(image.size)
    cover = ImageOps.fit(image, (min(side, COVER_SIZE),) * 2, Image.Resampling.LANCZOS)
    preview = cover.copy()
    preview.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE), Image.Resampling.LANCZOS)
    return Processed(original=_webp(cover, 88), extension=".webp", preview=_webp(preview, 80))
