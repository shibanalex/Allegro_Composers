"""Passwords, login tokens, one-time links and encrypted e-mail addresses"""
import base64
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from cryptography.fernet import Fernet, InvalidToken

from allegro.core.config import settings

# ---------------------------------------------------------------- passwords (stdlib scrypt)

_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1, "dklen": 32}


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(digest).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, digest_b64 = stored.split("$")
        digest = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64), **_SCRYPT)
        return hmac.compare_digest(digest, base64.b64decode(digest_b64))
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------- login tokens (JWT)

def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expire}, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> Optional[uuid.UUID]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return uuid.UUID(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        return None


# ---------------------------------------------------------------- one-time links (invitations, password resets)

def new_link_token() -> str:
    """The secret part of a link; only its hash is stored, so a database leak can't be turned into accounts"""
    return secrets.token_urlsafe(24)


def link_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------- e-mail addresses
# Stored encrypted (Fernet), plus a keyed hash to find an account by e-mail and keep addresses unique.
# A copy of the database alone reveals no addresses.

def _derive(label: bytes) -> bytes:
    base = (settings.email_encryption_key or settings.secret_key).encode()
    return hmac.new(base, label, hashlib.sha256).digest()


_fernet = Fernet(base64.urlsafe_b64encode(_derive(b"allegro:email-encryption")))
_index_key = _derive(b"allegro:email-index")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def email_index(email: str) -> str:
    return hmac.new(_index_key, normalize_email(email).encode(), hashlib.sha256).hexdigest()


def encrypt_email(email: str) -> str:
    return _fernet.encrypt(normalize_email(email).encode()).decode()


def decrypt_email(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return _fernet.decrypt(value.encode()).decode()
    except InvalidToken:  # encrypted with another key (SECRET_KEY changed): the address is lost, not the account
        return None
