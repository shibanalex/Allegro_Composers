"""File storage: local disk for development, S3-compatible object storage (Yandex Object Storage, Cloudflare R2, MinIO...) in production.

Both keep files under keys like "audios/<username>/<random>_<name>" and expose the same methods,
so services never know which one is in use. Free hosting wipes its own disk on every restart,
which is why deployed sites keep uploads in object storage (STORAGE_BACKEND=s3).
"""
import mimetypes
import re
import tempfile
import uuid
from pathlib import Path
from typing import BinaryIO, Iterator, Optional

from fastapi import UploadFile
from starlette.concurrency import run_in_threadpool

from allegro.core.config import settings

CHUNK = 1024 * 1024


class UploadTooLarge(ValueError):
    pass


def content_type_for(key: str) -> str:
    # From the extension, never from what the uploader's browser claimed
    return mimetypes.guess_type(key)[0] or "application/octet-stream"


class _BaseStorage:
    def __init__(self, url_prefix: str):
        self.url_prefix = url_prefix.rstrip("/")

    @staticmethod
    def _safe_name(filename: str) -> str:
        name = Path(filename or "file").name
        name = re.sub(r"[^\w.\-]+", "_", name, flags=re.UNICODE).strip("._")
        return name[:100] or "file"

    @staticmethod
    def _check_key(key: str) -> str:
        if not key or key.startswith("/") or "\\" in key or ".." in key.split("/"):
            raise ValueError("Invalid key")
        return key

    def new_key(self, folder: str, filename: str) -> str:
        return f"{folder}/{uuid.uuid4().hex[:12]}_{self._safe_name(filename)}"

    def url(self, key: Optional[str]) -> Optional[str]:
        return f"{self.url_prefix}/{key}" if key else None

    def key_from_url(self, url: Optional[str]) -> Optional[str]:
        prefix = self.url_prefix + "/"
        return url[len(prefix):] if url and url.startswith(prefix) else None

    async def _spool(self, file: UploadFile) -> tuple[BinaryIO, int]:
        """Read the upload into a temporary file, stopping at the size limit"""
        limit = settings.max_upload_mb * 1024 * 1024
        spool = tempfile.SpooledTemporaryFile(max_size=8 * CHUNK)
        size = 0
        while chunk := await file.read(CHUNK):
            size += len(chunk)
            if size > limit:
                spool.close()
                raise UploadTooLarge(f"Файл больше {settings.max_upload_mb} МБ")
            spool.write(chunk)
        spool.seek(0)
        return spool, size

    async def save_upload(self, file: UploadFile, folder: str) -> dict:
        key = self.new_key(folder, file.filename)
        spool, size = await self._spool(file)
        with spool:
            # boto3 and disk writes block: in a worker thread, so other requests keep being served meanwhile
            await run_in_threadpool(self._put, key, spool)
        return {
            "key": key,
            "url": self.url(key),
            "name": file.filename or key,
            "content_type": content_type_for(key),
            "size": size,
        }

    def save_bytes(self, key: str, data: bytes) -> str:
        import io

        self._put(self._check_key(key), io.BytesIO(data))
        return self.url(key)

    # Implemented by each backend
    def _put(self, key: str, stream: BinaryIO) -> None: ...
    def read_bytes(self, key: str) -> bytes: ...
    def open_stream(self, key: str) -> Optional[Iterator[bytes]]: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: Optional[str]) -> None: ...


class LocalStorage(_BaseStorage):
    is_local = True

    def __init__(self, root: str, url_prefix: str):
        super().__init__(url_prefix)
        self.root = Path(root)

    def path(self, key: str) -> Path:
        path = (self.root / self._check_key(key)).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("Invalid key")
        return path

    def _put(self, key: str, stream: BinaryIO) -> None:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as out:
            while chunk := stream.read(CHUNK):
                out.write(chunk)

    def read_bytes(self, key: str) -> bytes:
        return self.path(key).read_bytes()

    def open_stream(self, key: str) -> Optional[Iterator[bytes]]:
        path = self.path(key)
        if not path.is_file():
            return None

        def chunks():
            with path.open("rb") as f:
                while chunk := f.read(CHUNK):
                    yield chunk

        return chunks()

    def exists(self, key: str) -> bool:
        return self.path(key).is_file()

    def delete(self, key: Optional[str]) -> None:
        if key:
            self.path(key).unlink(missing_ok=True)


class S3Storage(_BaseStorage):
    """Any S3-compatible bucket. Files are served straight from the bucket's public address
    (MEDIA_URL_PREFIX), i.e. from another origin than the site - uploads can never run scripts on it."""
    is_local = False

    def __init__(self, url_prefix: str):
        super().__init__(url_prefix)
        import boto3
        from botocore.config import Config

        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )

    def _put(self, key: str, stream: BinaryIO) -> None:
        self.client.upload_fileobj(
            stream, self.bucket, key,
            ExtraArgs={"ContentType": content_type_for(key), "CacheControl": "public, max-age=604800"},
        )

    def read_bytes(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=self._check_key(key))["Body"].read()

    def open_stream(self, key: str) -> Optional[Iterator[bytes]]:
        try:
            body = self.client.get_object(Bucket=self.bucket, Key=self._check_key(key))["Body"]
        except self.client.exceptions.NoSuchKey:
            return None
        return body.iter_chunks(CHUNK)

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=self._check_key(key))
            return True
        except Exception:
            return False

    def delete(self, key: Optional[str]) -> None:
        if key:
            self.client.delete_object(Bucket=self.bucket, Key=self._check_key(key))


def _make_storage():
    if settings.storage_backend == "s3":
        return S3Storage(settings.media_url_prefix)
    return LocalStorage(settings.media_dir, settings.media_url_prefix)


storage = _make_storage()
