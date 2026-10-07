"""References to uploaded files in what users send: a user may attach only their own uploads.

Uploads are stored as <folder>/<username>/<random>_<name> (see the media module), so the owner of a
file is the second segment of its key. Without this check anyone could point their opus or post at
someone else's file - download a paid score through their own opus, or delete the file with it.
A reference already attached to the same object stays allowed (demo content uses shared seed files).

Files are removed only after the database change is committed (`after_commit`), never before.
"""
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from allegro.core.db import after_commit
from allegro.core.errors import Invalid
from allegro.core.images import is_picture, preview_key
from allegro.core.peaks import is_audio, peaks_key
from allegro.core.storage import storage


def owns_key(username: str, key: Optional[str]) -> bool:
    parts = (key or "").split("/")
    return len(parts) >= 3 and parts[1] == username and ".." not in parts


def check_key(username: str, key: Optional[str], keep: Iterable[Optional[str]] = ()) -> None:
    """A storage key (opus score, MusicXML, audio)"""
    if key and key not in set(keep) and not owns_key(username, key):
        raise Invalid("Можно прикрепить только файл, загруженный вами")


def check_url(username: str, url: Optional[str], keep: Iterable[Optional[str]] = ()) -> None:
    """A /media/... URL (covers, avatars, attachments); links to other sites are not accepted here"""
    if not url or url in set(keep):
        return
    key = storage.key_from_url(url)
    if key is None or not owns_key(username, key):
        raise Invalid("Можно прикрепить только файл, загруженный вами")


def delete_own_after_commit(db: Session, username: str, key: Optional[str]) -> None:
    """Remove a replaced/deleted file once the change is saved - but never one that belongs to someone else"""
    if key and owns_key(username, key):
        after_commit(db, lambda: storage.delete(key))
        if is_picture(key):
            after_commit(db, lambda: storage.delete(preview_key(key)))
        if is_audio(key):
            after_commit(db, lambda: storage.delete(peaks_key(key)))


def delete_own_url_after_commit(db: Session, username: str, url: Optional[str]) -> None:
    delete_own_after_commit(db, username, storage.key_from_url(url))
