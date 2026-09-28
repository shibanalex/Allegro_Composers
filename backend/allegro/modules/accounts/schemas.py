"""Public data shapes of the accounts module (other modules embed UserBrief)"""
import re
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from allegro.core.schemas import ORMModel, UTCDateTime
from allegro.modules.accounts.roles import HALL_THEMES, Role

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")
# Addresses the site itself uses: nobody may take them as a username
RESERVED = {
    "admin", "api", "media", "library", "search", "create", "settings", "login", "register", "opus", "posts",
    "setup", "about", "news", "feedback", "reset", "performances", "invite",
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

RoleName = Literal["composer", "theorist", "performer", "listener"]
HallTheme = Literal["baroque", "romantic", "modern", "avantgarde"]


class UserBrief(ORMModel):
    id: uuid.UUID
    username: str
    display_name: str
    pseudonym: Optional[str] = None
    avatar_url: Optional[str] = None
    role: str = Role.LISTENER


class Link(BaseModel):
    label: str = Field(max_length=60)
    url: str = Field(max_length=512)

    @field_validator("url")
    @classmethod
    def _http_only(cls, v: str) -> str:
        if not re.match(r"^(https?://|mailto:)", v):
            raise ValueError("Ссылка должна начинаться с http://, https:// или mailto:")
        return v


def _username(v: str) -> str:
    v = v.strip().lower()
    if not USERNAME_RE.match(v):
        raise ValueError("3–32 символа: латиница, цифры и _")
    if v in RESERVED:
        raise ValueError("Это имя зарезервировано")
    return v


def _optional_email(v: Optional[str]) -> Optional[str]:
    if v is None or not v.strip():
        return None
    v = v.strip().lower()
    if not EMAIL_RE.match(v):
        raise ValueError("Некорректный email")
    return v


class RegisterIn(BaseModel):
    invite: Optional[str] = Field(None, max_length=128)
    username: str
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role: RoleName = "listener"
    email: Optional[str] = Field(None, max_length=255)  # optional: only for restoring access later

    @field_validator("username")
    @classmethod
    def _check_username(cls, v: str) -> str:
        return _username(v)

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: Optional[str]) -> Optional[str]:
        return _optional_email(v)


class SetupIn(BaseModel):
    code: str = Field(max_length=256)
    username: str
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=128)  # the site's owner: a long password
    role: RoleName = "composer"
    email: Optional[str] = Field(None, max_length=255)

    @field_validator("username")
    @classmethod
    def _check_username(cls, v: str) -> str:
        return _username(v)

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: Optional[str]) -> Optional[str]:
        return _optional_email(v)


class LoginIn(BaseModel):
    login: str = Field(max_length=255)  # username or email
    password: str = Field(max_length=128)


class ProfileOut(ORMModel):
    id: uuid.UUID
    username: str
    display_name: str
    pseudonym: Optional[str] = None
    bio: Optional[str] = None
    about_md: Optional[str] = None
    avatar_url: Optional[str] = None
    links: list[Link] = []
    role: str
    hall_theme: str
    created_at: UTCDateTime
    stats: dict[str, int] = {}  # counts contributed by other modules: opuses, posts, articles, performances...


class MeOut(ProfileOut):
    email: Optional[str] = None
    is_admin: bool
    capabilities: list[str]


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
    links: Optional[list[Link]] = Field(None, max_length=20)
    role: Optional[RoleName] = None
    hall_theme: Optional[HallTheme] = None
    email: Optional[str] = Field(None, max_length=255)  # "" removes it

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: Optional[str]) -> Optional[str]:
        return v if v == "" else _optional_email(v)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class SiteConfig(BaseModel):
    registration: Literal["closed", "invite", "open"]
    registration_open: bool  # kept for older clients: anyone may sign up
    setup_available: bool
    roles: dict[str, str]
    hall_themes: dict[str, str]


# ---------------------------------------------------------------- one-time links

class LinkCheckOut(BaseModel):
    valid: bool
    purpose: Optional[str] = None
    role: Optional[str] = None  # invitation: the suggested role
    inviter: Optional[str] = None
    username: Optional[str] = None  # reset: whose password it resets


class ResetIn(BaseModel):
    token: str = Field(max_length=128)
    password: str = Field(min_length=8, max_length=128)


class InviteIn(BaseModel):
    note: Optional[str] = Field(None, max_length=200)
    role: Optional[RoleName] = None


class AccessLinkOut(ORMModel):
    id: uuid.UUID
    purpose: str
    note: Optional[str] = None
    role: Optional[str] = None
    created_at: UTCDateTime
    expires_at: UTCDateTime
    used_at: Optional[UTCDateTime] = None
    revoked_at: Optional[UTCDateTime] = None
    used_by: Optional[UserBrief] = None
    target_user: Optional[UserBrief] = None
    token: Optional[str] = None  # only right after creation: the link is shown once
    status: str = "active"  # active | used | expired | revoked


class AdminUserOut(UserBrief):
    is_admin: bool
    is_hidden: bool
    has_email: bool = False  # the address itself is never shown to administrators
    created_at: UTCDateTime


class AdminUserUpdate(BaseModel):
    is_hidden: Optional[bool] = None
    is_admin: Optional[bool] = None
