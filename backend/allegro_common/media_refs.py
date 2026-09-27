"""References to uploaded files in what users send: a user may attach only their own uploads.

Uploads are stored as <folder>/<username>/<random>_<name> (see the media service), so the owner of a
file is the second segment of its key. Without this check anyone could point their opus or post at
someone else's file - download a paid score through their own opus, or delete the file with it.
A reference already attached to the same object stays allowed (demo content uses shared seed files).
"""
from typing import Iterable, Optional

from fastapi import HTTPException

from allegro_common.models import User
from allegro_common.storage import storage


def owns_key(user: User, key: Optional[str]) -> bool:
    parts = (key or "").split("/")
    return len(parts) >= 3 and parts[1] == user.username and ".." not in parts


def check_key(user: User, key: Optional[str], keep: Iterable[Optional[str]] = ()) -> None:
    """A storage key (opus score, MusicXML, audio)"""
    if key and key not in set(keep) and not owns_key(user, key):
        raise HTTPException(422, "Можно прикрепить только файл, загруженный вами")


def check_url(user: User, url: Optional[str], keep: Iterable[Optional[str]] = ()) -> None:
    """A /media/... URL (covers, avatars, attachments); links to other sites are not accepted here"""
    if not url or url in set(keep):
        return
    key = storage.key_from_url(url)
    if key is None or not owns_key(user, key):
        raise HTTPException(422, "Можно прикрепить только файл, загруженный вами")


def delete_own(user: User, key: Optional[str]) -> None:
    """Remove a replaced/deleted file - but never one that belongs to someone else (or to the seed)"""
    if key and owns_key(user, key):
        storage.delete(key)
