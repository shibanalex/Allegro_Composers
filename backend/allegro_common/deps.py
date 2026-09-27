"""FastAPI dependencies shared by services"""
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from allegro_common.config import settings
from allegro_common.db import get_db
from allegro_common.models import User
from allegro_common.security import decode_access_token

TOKEN_COOKIE = "allegro_token"


def _token_from_request(request: Request) -> Optional[str]:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get(TOKEN_COOKIE)


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = _token_from_request(request)
    user_id = decode_access_token(token) if token else None
    user = db.get(User, user_id) if user_id else None
    # A shadowed account, or one outside the invite list, keeps no access even with an old token
    if user and (user.is_hidden or not settings.login_allowed(user.username)):
        return None
    return user


def get_current_user(user: Optional[User] = Depends(get_optional_user)) -> User:
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется вход")
    return user
