"""FastAPI dependencies: who is making the request and what they may do (used by every module's HTTP layer)"""
from typing import Optional

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from allegro.core.config import settings
from allegro.core.db import get_db
from allegro.core.errors import Forbidden, Unauthorized
from allegro.core.ratelimit import client_ip
from allegro.core.security import decode_access_token
from allegro.modules.accounts import service
from allegro.modules.accounts.models import User
from allegro.modules.accounts.roles import CAPABILITY_REFUSALS, Capability, can

TOKEN_COOKIE = "allegro_token"  # HttpOnly: page scripts can't read it, so injected code can't steal it
SESSION_COOKIE = "allegro_session"  # not secret: only tells the site's pages that someone is signed in
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _allowed_origins() -> set[str]:
    values = [settings.public_url, settings.site_url, settings.render_external_url, *settings.cors_origins.split(",")]
    return {v.strip().rstrip("/") for v in values if v.strip()}


def _same_site(request: Request) -> bool:
    """CSRF: a request that changes something with the login cookie must come from the site's own pages.
    Browsers say where a request comes from (Sec-Fetch-Site); older ones send at least Origin."""
    fetch_site = request.headers.get("sec-fetch-site")
    if fetch_site:
        return fetch_site in ("same-origin", "none")
    origin = request.headers.get("origin")
    return not origin or origin.rstrip("/") in _allowed_origins()


def _token_from_request(request: Request) -> Optional[str]:
    """The Authorization header (the site's server rendering, API clients) or the login cookie (browsers)"""
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    token = request.cookies.get(TOKEN_COOKIE)
    if token and request.method not in SAFE_METHODS and not _same_site(request):
        raise Forbidden("Запрос пришёл с чужого сайта и отклонён")
    return token


def set_login_cookie(request: Request, response: Response, token: str) -> None:
    secure = settings.cookie_secure
    if secure is None:  # on Render the site's own address is https; elsewhere; what the proxy says
        secure = settings.render_external_url.startswith("https://") or             request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    age = settings.access_token_expire_minutes * 60
    response.set_cookie(TOKEN_COOKIE, token, max_age=age, httponly=True, secure=secure, samesite="lax", path="/")
    response.set_cookie(SESSION_COOKIE, "1", max_age=age, httponly=False, secure=secure, samesite="lax", path="/")


def clear_login_cookie(response: Response) -> None:
    response.delete_cookie(TOKEN_COOKIE, path="/")
    response.delete_cookie(SESSION_COOKIE, path="/")


def client_address(request: Request) -> str:
    return client_ip(request)


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    token = _token_from_request(request)
    claims = decode_access_token(token) if token else None
    return service.get_active_user(db, *claims) if claims else None


def get_current_user(user: Optional[User] = Depends(get_optional_user)) -> User:
    if not user:
        raise Unauthorized("Требуется вход")
    return user


def get_admin(user: User = Depends(get_current_user)) -> User:
    """Running the site: members' rights, pages, feedback answers (same as require(Capability.MANAGE_SITE))"""
    if not can(user, Capability.MANAGE_SITE):
        raise Forbidden(CAPABILITY_REFUSALS[Capability.MANAGE_SITE])
    return user


def require(capability: Capability):
    """Dependency factory: the signed-in member must be allowed to do this (by role, or as an administrator)"""
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not can(user, capability):
            raise Forbidden(CAPABILITY_REFUSALS[capability])
        return user
    return dependency
