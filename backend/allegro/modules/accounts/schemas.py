"""Public data shapes of the accounts module (other modules embed UserBrief)"""
import re
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from allegro.core.schemas import Line, Name, ORMModel, UTCDateTime
from allegro.core.slugs import transliterate
from allegro.modules.accounts.roles import HALL_THEMES, Role

# The hall's address (/@ivan.petrov): Latin letters, digits and _ . - inside; starts and ends with a letter or digit
USERNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{1,30})[a-z0-9]$")
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


def normalize_username(value: str) -> str:
    """A ready address to offer instead of what was typed: «Иван Петров» → ivan_petrov"""
    v = transliterate(value.strip())
    v = re.sub(r"\s+", "_", v)
    v = re.sub(r"[^a-z0-9._-]", "", v)
    v = re.sub(r"([._-])[._-]+", r"\1", v)  # no «..», «_-» and the like
    return v.strip("._-")[:32].strip("._-")


def _count(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return f"{n} {one}"
    return f"{n} {few}" if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else f"{n} {many}"


def username_problems(value: str) -> list[str]:
    """Everything that is wrong with an address, in words a person understands (empty: it is fine)"""
    v = value.strip().lower()
    problems = []
    if re.search(r"[а-яё]", v):
        problems.append("Русские буквы нельзя — только латиница")
    if re.search(r"\s", v):
        problems.append("Пробелы нельзя — вместо них _ или точка")
    odd = sorted({c for c in v if not re.match(r"[a-z0-9._\-а-яё\s]", c)})
    if odd:
        problems.append("Нельзя использовать: " + " ".join(odd))
    if len(v) < 3:
        problems.append(f"Слишком коротко: нужно ещё {_count(3 - len(v), 'символ', 'символа', 'символов')}")
    if len(v) > 32:
        problems.append(f"Слишком длинно: уберите {_count(len(v) - 32, 'символ', 'символа', 'символов')}")
    if v and (v[0] in "._-" or v[-1] in "._-"):
        problems.append("Начало и конец — буква или цифра, не . _ -")
    if re.search(r"[._-]{2}", v):
        problems.append("Два знака подряд (.. __ -_) нельзя")
    if not problems and v in RESERVED:
        problems.append("Этот адрес занят самим сайтом")
    return problems


def _username(v: str) -> str:
    problems = username_problems(v)
    if problems:
        raise ValueError(". ".join(problems))
    return v.strip().lower()


class UsernameCheck(BaseModel):
    ok: bool
    problems: list[str] = []  # what is wrong, for a person to read
    suggestions: list[str] = []  # free addresses close to what was typed


def _optional_email(v: Optional[str]) -> Optional[str]:
    if v is None or not v.strip():
        return None
    v = v.strip().lower()
    if not EMAIL_RE.match(v):
        raise ValueError("Некорректный email")
    return v


class RegisterIn(BaseModel):
    username: str
    display_name: Name = Field(min_length=1, max_length=120)
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
    display_name: Name = Field(min_length=1, max_length=120)
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


HallAccent = Literal["gold", "silver", "copper", "crimson", "emerald", "sapphire"]
HallTab = Literal["exhibition", "library", "articles", "performances", "blog", "materials", "about"]


class HallSettings(BaseModel):
    """How a member arranges their hall (the style itself is `hall_theme`)"""
    cover_url: Optional[str] = Field(None, max_length=512)  # a banner behind the hall's heading
    epigraph: Optional[str] = Field(None, max_length=300)  # a line under the name: a motto, a quotation
    epigraph_source: Optional[str] = Field(None, max_length=120)
    accent: Optional[HallAccent] = None  # None: the style's own colour
    tabs: Optional[list[HallTab]] = Field(None, max_length=7)  # visible tabs in this order; None: the role's default
    pinned_post: Optional[str] = Field(None, max_length=255)  # slug of a blog post shown first

    @field_validator("tabs")
    @classmethod
    def _tabs(cls, v):
        if v is not None and not v:
            raise ValueError("Оставьте хотя бы одну вкладку")
        return list(dict.fromkeys(v)) if v else v


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
    hall: HallSettings = HallSettings()
    created_at: UTCDateTime
    stats: dict[str, int] = {}  # counts contributed by other modules: opuses, posts, articles, performances...

    @field_validator("hall", mode="before")
    @classmethod
    def _hall(cls, v):
        return v or {}


class MeOut(ProfileOut):
    email: Optional[str] = None
    is_admin: bool
    is_moderator: bool = False
    seen_hints: list[str] = []

    @field_validator("seen_hints", mode="before")
    @classmethod
    def _hints(cls, v):
        return v or []
    capabilities: list[str]


class TokenOut(BaseModel):
    """After signing in: the member; the login token itself is in an HttpOnly cookie, never in the answer
    (a script injected into a page could read an answer, not that cookie)"""
    user: MeOut


class ProfileUpdate(BaseModel):
    display_name: Optional[Name] = Field(None, min_length=1, max_length=120)
    pseudonym: Optional[Line] = Field(None, max_length=120)
    bio: Optional[str] = Field(None, max_length=400)
    about_md: Optional[str] = Field(None, max_length=20_000)
    avatar_url: Optional[str] = Field(None, max_length=512)
    links: Optional[list[Link]] = Field(None, max_length=20)
    role: Optional[RoleName] = None
    hall_theme: Optional[HallTheme] = None
    hall: Optional[HallSettings] = None
    email: Optional[str] = Field(None, max_length=255)  # "" removes it

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: Optional[str]) -> Optional[str]:
        return v if v == "" else _optional_email(v)


class HintsIn(BaseModel):
    hints: list[str] = Field(max_length=100)

    @field_validator("hints")
    @classmethod
    def _names(cls, v: list[str]) -> list[str]:
        if not all(re.fullmatch(r"[a-z0-9-]{1,40}", h) for h in v):
            raise ValueError("неизвестная подсказка")
        return v


class PasswordChangeIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class SiteConfig(BaseModel):
    setup_available: bool
    roles: dict[str, str]
    hall_themes: dict[str, str]


# ---------------------------------------------------------------- one-time links

class LinkCheckOut(BaseModel):
    valid: bool
    purpose: Optional[str] = None
    username: Optional[str] = None  # whose password it resets


class ResetIn(BaseModel):
    token: str = Field(max_length=128)
    password: str = Field(min_length=8, max_length=128)


class AccessLinkOut(ORMModel):
    id: uuid.UUID
    purpose: str
    note: Optional[str] = None
    created_at: UTCDateTime
    expires_at: UTCDateTime
    used_at: Optional[UTCDateTime] = None
    revoked_at: Optional[UTCDateTime] = None
    target_user: Optional[UserBrief] = None
    token: Optional[str] = None  # only right after creation: the link is shown once
    status: str = "active"  # active | used | expired | revoked


class AdminUserOut(UserBrief):
    is_admin: bool
    is_moderator: bool = False
    is_hidden: bool
    has_email: bool = False  # the address itself is never shown to administrators
    created_at: UTCDateTime


class AdminUserUpdate(BaseModel):
    is_hidden: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_moderator: Optional[bool] = None
