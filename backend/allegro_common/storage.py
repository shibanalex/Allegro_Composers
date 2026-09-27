"""File storage. Local disk for now; an S3/R2 implementation only needs the same four methods."""
import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from allegro_common.config import settings


class UploadTooLarge(ValueError):
    pass


class LocalStorage:
    def __init__(self, root: str, url_prefix: str):
        self.root = Path(root)
        self.url_prefix = url_prefix.rstrip("/")

    @staticmethod
    def _safe_name(filename: str) -> str:
        name = Path(filename or "file").name
        name = re.sub(r"[^\w.\-]+", "_", name, flags=re.UNICODE).strip("._")
        return name[:100] or "file"

    def new_key(self, folder: str, filename: str) -> str:
        return f"{folder}/{uuid.uuid4().hex[:12]}_{self._safe_name(filename)}"

    def path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("Invalid key")
        return path

    def url(self, key: str | None) -> str | None:
        return f"{self.url_prefix}/{key}" if key else None

    async def save_upload(self, file: UploadFile, folder: str) -> dict:
        key = self.new_key(folder, file.filename)
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        limit = settings.max_upload_mb * 1024 * 1024
        size = 0
        with target.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    out.close()
                    target.unlink(missing_ok=True)
                    raise UploadTooLarge(f"Файл больше {settings.max_upload_mb} МБ")
                out.write(chunk)
        return {
            "key": key,
            "url": self.url(key),
            "name": file.filename or key,
            "content_type": file.content_type or "application/octet-stream",
            "size": size,
        }

    def save_bytes(self, key: str, data: bytes) -> str:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return self.url(key)

    def delete(self, key: str | None) -> None:
        if key:
            self.path(key).unlink(missing_ok=True)

    def key_from_url(self, url: str | None) -> str | None:
        prefix = self.url_prefix + "/"
        return url[len(prefix):] if url and url.startswith(prefix) else None


storage = LocalStorage(settings.media_dir, settings.media_url_prefix)
