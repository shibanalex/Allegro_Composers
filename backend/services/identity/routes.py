"""Identity service: registration, login, public profiles (the author's salon header)"""
import re
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from allegro_common.db import get_db
from allegro_common.deps import get_current_user
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
    login: str  # username or email
    password: str


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
    about_md: Optional[str] = None
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


@router.post("/api/auth/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    login_value = data.login.strip().lower()
    user = db.scalar(select(User).where(or_(User.username == login_value, User.email == login_value)))
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный логин или пароль")
    return TokenOut(access_token=create_access_token(user.id), user=_me(db, user))


@router.get("/api/auth/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _me(db, user)


@router.patch("/api/users/me", response_model=MeOut)
def update_me(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    return _me(db, user)


@router.get("/api/users/{username}", response_model=ProfileOut)
def get_profile(username: str, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == username.lower()))
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Автор не найден")
    return ProfileOut.model_validate(user).model_copy(update={"stats": _stats(db, user)})
