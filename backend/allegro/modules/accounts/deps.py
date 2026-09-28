"""FastAPI dependencies: who is making the request and what they may do (used by every module's HTTP layer)"""
from typing import Optional

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from allegro.core.db import get_db
from allegro.core.errors import Forbidden, Unauthorized
from allegro.core.security import decode_access_token
from allegro.modules.accounts import service
from allegro.modules.accounts.models import User
from allegro.modules.accounts.roles import CAPABILITY_REFUSALS, Capability, can

TOKEN_COOKIE = "allegro_token"


def _token_from_request(request: Request) -> Optional[str]:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.cookies.get(TOKEN_COOKIE)


def client_address(request: Request) -> str:
    return request.client.host if request.client else ""


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = _token_from_request(request)
    user_id = decode_access_token(token) if token else None
    return service.get_active_user(db, user_id) if user_id else None


def get_current_user(user: Optional[User] = Depends(get_optional_user)) -> User:
    if not user:
        raise Unauthorized("Требуется вход")
    return user


def get_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise Forbidden("Только для администраторов")
    return user


def require(capability: Capability):
    """Dependency factory: the signed-in member must be allowed to do this (by role, or as an administrator)"""
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not can(user, capability):
            raise Forbidden(CAPABILITY_REFUSALS[capability])
        return user
    return dependency
