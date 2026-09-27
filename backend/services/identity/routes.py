"""Identity service: registration, login, public profiles (the author's salon header)"""
import hmac
import re
import secrets
import threading
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from allegro_common.config import settings
from allegro_common.db import get_db
from allegro_common.deps import get_current_user
from allegro_common.media_refs import check_url
from allegro_common.models import Collection, Opus, Post, User
from allegro_common.schemas import ORMModel, UTCDateTime
from allegro_common.security import create_access_token, hash_password, verify_password

router = APIRouter(tags=["identity"])

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")
RESERVED = {"admin", "api", "media", "library", "search", "create", "settings", "login", "register", "opus", "posts"}


class Link(BaseModel):
    label: str = Field(max_length=60)
    url: str = Field(max_length=512)

    @field_validator("url")
    @classmethod
    def _http_only(cls, v: str) -> str:
        if not re.match(r"^(https?://|mailto:)", v):
            raise ValueError("Ссылка должна начинаться с http://, https:// или mailto:")
        return v


class RegisterIn(BaseModel):
    username: str
    email: str = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        v = v.strip().lower()
        if not USERNAME_RE.match(v):
            raise ValueError("3–32 символа: латиница, цифры и _")
        if v in RESERVED:
            raise ValueError("Это имя зарезервировано")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Некорректный email")
        return v


class LoginIn(BaseModel):
    login: str = Field(max_length=255)  # username or email
    password: str = Field(max_length=128)


class ProfileStats(BaseModel):
    opuses: int
    posts: int
    collections: int


class ProfileOut(ORMModel):
    id: uuid.UUID
    username: str
    display_name: str
    pseudonym: Optional[str] = None
    bio: Optional[str] = None
    about_md: Optional[str] = None
    avatar_url: Optional[str] = None
    links: list[Link] = []
    created_at: UTCDateTime
    stats: Optional[ProfileStats] = None


class MeOut(ProfileOut):
    email: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: MeOut


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=120)
    pseudonym: Optional[str] = Field(None, max_length=120)
    bio: Optional[str] = Field(None, max_length=400)
    about_md: Optional[str] = Field(None, max_length=20_000)
    avatar_url: Optional[str] = Field(None, max_length=512)
    links: Optional[list[Link]] = None


def _stats(db: Session, user: User) -> ProfileStats:
    def count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(model.author_id == user.id, *where))

    return ProfileStats(
        opuses=count(Opus, Opus.status == "published"),
        posts=count(Post, Post.status == "published", Post.kind != "workshop"),
        collections=count(Collection),
    )


def _me(db: Session, user: User) -> MeOut:
    return MeOut.model_validate(user).model_copy(update={"stats": _stats(db, user)})


@router.post("/api/auth/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if not settings.registration_open:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Регистрация пока закрыта")
    taken = db.scalar(select(User).where(or_(User.username == data.username, User.email == data.email)))
    if taken:
        field = "Имя пользователя" if taken.username == data.username else "Email"
        raise HTTPException(status.HTTP_409_CONFLICT, f"{field} уже занят")
    user = User(
        username=data.username, email=data.email, password_hash=hash_password(data.password),
        display_name=data.display_name.strip(), links=[],
    )
    db.add(user)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id), user=_me(db, user))


# ---------------------------------------------------------------- password guessing

LOGIN_WINDOW_SECONDS = 15 * 60
LOGIN_MAX_FAILURES = 10
_failures: dict[tuple[str, str], list[float]] = {}
_failures_lock = threading.Lock()
# Unknown logins still pay for one hash, so the response time doesn't tell which accounts exist
_DUMMY_HASH = hash_password(secrets.token_hex(16))


def _recent_failures(key: tuple[str, str], now: float) -> list[float]:
    recent = [t for t in _failures.get(key, []) if now - t < LOGIN_WINDOW_SECONDS]
    if recent:
        _failures[key] = recent
    else:
        _failures.pop(key, None)
    return recent


@router.post("/api/auth/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    login_value = data.login.strip().lower()
    # Per login and address: 10 wrong passwords, then a pause until the oldest attempt is 15 minutes old.
    # (In one process; behind a proxy run uvicorn with --proxy-headers so the address is the visitor's.)
    key = (login_value, request.client.host if request.client else "")
    now = time.monotonic()
    with _failures_lock:
        recent = _recent_failures(key, now)
        if len(recent) >= LOGIN_MAX_FAILURES:
            wait = int(LOGIN_WINDOW_SECONDS - (now - recent[0])) // 60 + 1
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Слишком много попыток. Попробуйте через {wait} мин.")
    user = db.scalar(select(User).where(or_(User.username == login_value, User.email == login_value)))
    if not verify_password(data.password, user.password_hash if user else _DUMMY_HASH) or not user:
        with _failures_lock:
            _failures.setdefault(key, []).append(now)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль")
    with _failures_lock:
        _failures.pop(key, None)
    if user.is_hidden or not settings.login_allowed(user.username):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Вход пока закрыт")
    return TokenOut(access_token=create_access_token(user.id), user=_me(db, user))


class SiteConfig(BaseModel):
    registration_open: bool
    setup_available: bool


def _setup_available(db: Session) -> bool:
    return settings.setup_enabled and db.scalar(select(func.count()).select_from(User)) == 0


@router.get("/api/auth/config", response_model=SiteConfig)
def site_config(db: Session = Depends(get_db)):
    """What the frontend should offer: e.g. hide «Открыть свой зал» while sign-ups are closed"""
    return SiteConfig(registration_open=settings.registration_open, setup_available=_setup_available(db))


class SetupIn(RegisterIn):
    code: str = Field(max_length=256)
    password: str = Field(min_length=12, max_length=128)  # the only account that can publish: a long password


@router.post("/api/auth/setup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def first_setup(data: SetupIn, request: Request, db: Session = Depends(get_db)):
    """The very first account of a fresh site, created with the SETUP_TOKEN code from the hosting settings.
    Once any account exists this is closed for good, so nobody else can use it later."""
    if not _setup_available(db):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Первичная настройка уже выполнена")
    # Guessing the code is throttled like passwords
    key = ("#setup", request.client.host if request.client else "")
    now = time.monotonic()
    with _failures_lock:
        if len(_recent_failures(key, now)) >= LOGIN_MAX_FAILURES:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много попыток. Попробуйте позже.")
    if not hmac.compare_digest(data.code.strip().encode(), settings.setup_token.encode()):
        with _failures_lock:
            _failures.setdefault(key, []).append(now)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Неверный код настройки")
    if not settings.login_allowed(data.username):
        # Otherwise the new account could never log in again
        raise HTTPException(422, "Этого имени нет в LOGIN_ALLOWLIST в настройках хостинга")
    user = User(
        username=data.username, email=data.email, password_hash=hash_password(data.password),
        display_name=data.display_name.strip(), links=[],
    )
    db.add(user)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id), user=_me(db, user))


@router.get("/api/auth/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _me(db, user)


@router.patch("/api/users/me", response_model=MeOut)
def update_me(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if "avatar_url" in data.model_fields_set:
        check_url(user, data.avatar_url, [user.avatar_url])
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    return _me(db, user)


@router.get("/api/users", response_model=list[ProfileOut])
def list_composers(limit: int = 24, db: Session = Depends(get_db)):
    """The composers' halls, for the main page: the earliest members first"""
    users = db.scalars(
        select(User).where(User.is_hidden.is_(False)).order_by(User.created_at).limit(min(max(limit, 1), 100))
    ).all()
    return [ProfileOut.model_validate(u).model_copy(update={"stats": _stats(db, u)}) for u in users]


@router.get("/api/users/{username}", response_model=ProfileOut)
def get_profile(username: str, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == username.lower(), User.is_hidden.is_(False)))
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Автор не найден")
    return ProfileOut.model_validate(user).model_copy(update={"stats": _stats(db, user)})
