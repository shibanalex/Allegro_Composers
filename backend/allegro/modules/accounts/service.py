"""Use cases of the accounts module: joining, signing in, profiles, one-time links, administration.

Public API for other modules: `visible_authors`, `author_named`, `authors_matching`, `search_members`, `get_visible_user`,
`get_active_user`, `register_stat`, `stats_for` (and `roles.can`). Everything else here is used by this module's own HTTP layer.
"""
import hmac
import secrets
import uuid
from datetime import timedelta
from typing import Callable, Optional

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from allegro.core.config import settings
from allegro.core.errors import Conflict, Forbidden, Invalid, NotFound, Unauthorized
from allegro.core.files import check_url, delete_own_url_after_commit
from allegro.core.ratelimit import AttemptLimiter
from allegro.core.security import (
    decrypt_email, email_index, encrypt_email, hash_password, link_token_hash, new_link_token, verify_password,
)
from allegro.modules.accounts import repository as repo
from allegro.modules.accounts.models import AccessLink, User, aware, utcnow
from allegro.modules.accounts.roles import DEFAULT_HALL_THEME, HALL_THEMES, ROLE_LABELS, Role
from allegro.modules.accounts.schemas import ProfileUpdate, RegisterIn, SetupIn, SiteConfig

login_limiter = AttemptLimiter(10, 15 * 60, "Слишком много попыток входа.")
link_limiter = AttemptLimiter(10, 15 * 60, "Слишком много неверных ссылок.")
# Unknown logins still pay for one hash, so the response time doesn't tell which accounts exist
_DUMMY_HASH = hash_password(secrets.token_hex(16))


# ---------------------------------------------------------------- visibility (public)

def visible_authors(author_column):
    """SQL condition: the row's author is not in the shadow (shadowed accounts vanish from the site)"""
    return author_column.in_(repo.visible_user_ids())


def author_named(author_column, username: str):
    """SQL condition: the row's author has this username"""
    return author_column.in_(select(User.id).where(User.username == username.strip().lower()))


def authors_matching(author_column, needle: str):
    """SQL condition: the author's shown name contains the text (library search)"""
    return author_column.in_(select(User.id).where(func.lower(User.display_name).contains(needle, autoescape=True)))


def search_members(db: Session, words: list[str], limit: int) -> list[User]:
    """Search by words in names, pseudonyms and manifestos"""
    from allegro.core import textsearch

    return list(db.scalars(
        select(User).where(
            User.is_hidden.is_(False),
            textsearch.matches_all([User.username, User.display_name, User.pseudonym, User.bio], words),
        ).limit(limit)
    ))


def get_visible_user(db: Session, username: str) -> Optional[User]:
    return repo.by_username(db, username, visible_only=True)


def get_active_user(db: Session, user_id: uuid.UUID, session_version: int = 0) -> Optional[User]:
    """The account behind a login token — unless it was put in the shadow or its sessions were revoked since"""
    user = repo.by_id(db, user_id)
    if not user or user.is_hidden or user.session_version != session_version:
        return None
    return user


# ---------------------------------------------------------------- statistics contributed by other modules (public)

StatProvider = Callable[[Session, list[uuid.UUID]], dict[uuid.UUID, int]]
_stat_providers: dict[str, StatProvider] = {}


def register_stat(name: str, provider: StatProvider) -> None:
    """Another module adds a counter to profiles (catalog: opuses, performances; publications: posts…)"""
    _stat_providers[name] = provider


def stats_for(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
    result: dict[uuid.UUID, dict[str, int]] = {uid: {} for uid in user_ids}
    for name, provider in _stat_providers.items():
        counts = provider(db, user_ids) if user_ids else {}
        for uid in user_ids:
            result[uid][name] = counts.get(uid, 0)
    return result


# ---------------------------------------------------------------- site configuration

def setup_available(db: Session) -> bool:
    return settings.setup_enabled and repo.count_users(db) == 0


def site_config(db: Session) -> SiteConfig:
    mode = settings.effective_registration_mode
    return SiteConfig(
        registration=mode, registration_open=mode == "open", setup_available=setup_available(db),
        roles={r.value: label for r, label in ROLE_LABELS.items()}, hall_themes=HALL_THEMES,
    )


# ---------------------------------------------------------------- signing in and joining

def login(db: Session, login_value: str, password: str, client: str) -> User:
    # Per login and address: 10 wrong passwords, then a pause until the oldest attempt is 15 minutes old
    key = (login_value.strip().lower(), client)
    login_limiter.check(key)
    user = repo.by_login(db, login_value)
    if not verify_password(password, user.password_hash if user else _DUMMY_HASH) or not user:
        login_limiter.hit(key)
        raise Unauthorized("Неверный логин или пароль")
    login_limiter.reset(key)
    if user.is_hidden:
        raise Forbidden("Вход для этого аккаунта закрыт")
    return user


def _valid_link(db: Session, token: str, purpose: str, client: str) -> AccessLink:
    link_limiter.check((client,))
    link = repo.link_by_token(db, token) if token else None
    if not link or link.purpose != purpose or link.status != "active":
        link_limiter.hit((client,))
        raise Forbidden("Ссылка недействительна: её уже использовали, отозвали или срок истёк")
    return link


def _claim(db: Session, link: AccessLink, **values) -> None:
    """Mark a one-time link used in one statement: of two simultaneous uses only one wins"""
    claimed = db.execute(
        update(AccessLink)
        .where(AccessLink.id == link.id, AccessLink.used_at.is_(None), AccessLink.revoked_at.is_(None))
        .values(used_at=utcnow(), **values)
    ).rowcount
    if claimed != 1:
        db.rollback()
        raise Forbidden("Ссылка недействительна: её уже использовали, отозвали или срок истёк")


def _commit_new_user(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:  # the same name or e-mail taken by a simultaneous sign-up
        db.rollback()
        raise Conflict("Имя пользователя или email уже заняты")


def _new_user(db: Session, *, username: str, display_name: str, password: str, role: str, email: Optional[str], **extra) -> User:
    if repo.username_taken(db, username):
        raise Conflict("Имя пользователя уже занято")
    if email and repo.email_taken(db, email):
        raise Conflict("Этот email уже привязан к другому аккаунту")
    user = User(
        username=username, display_name=display_name.strip(), password_hash=hash_password(password),
        role=role, hall_theme=DEFAULT_HALL_THEME, links=[],
        email_hash=email_index(email) if email else None, email_encrypted=encrypt_email(email) if email else None,
        **extra,
    )
    db.add(user)
    return user


def register(db: Session, data: RegisterIn, client: str) -> User:
    mode = settings.effective_registration_mode
    if mode == "closed":
        raise Forbidden("Регистрация закрыта")
    link = None
    if mode == "invite" or data.invite:
        if not data.invite:
            raise Forbidden("Регистрация пока только по приглашениям")
        link = _valid_link(db, data.invite, "invite", client)
    user = _new_user(
        db, username=data.username, display_name=data.display_name, password=data.password, role=data.role,
        email=data.email, invited_by_id=link.created_by_id if link else None,
    )
    db.flush()
    if link:
        _claim(db, link, used_by_id=user.id)
    _commit_new_user(db)
    return user


def setup(db: Session, data: SetupIn, client: str) -> User:
    """The very first account of a fresh site: the owner, an administrator"""
    if not setup_available(db):
        raise NotFound("Первичная настройка уже выполнена")
    link_limiter.check(("#setup", client))
    if not hmac.compare_digest(data.code.strip().encode(), settings.setup_token.encode()):
        link_limiter.hit(("#setup", client))
        raise Forbidden("Неверный код настройки")
    user = _new_user(
        db, username=data.username, display_name=data.display_name, password=data.password, role=data.role,
        email=data.email, is_admin=True,
    )
    _commit_new_user(db)
    return user


# ---------------------------------------------------------------- one-time links

def check_link(db: Session, token: str) -> dict:
    link = repo.link_by_token(db, token)
    if not link or link.status != "active":
        return {"valid": False}
    return {
        "valid": True, "purpose": link.purpose, "role": link.role,
        "inviter": link.created_by.display_name if link.created_by else None,
        "username": link.target_user.username if link.target_user else None,
    }


def reset_password(db: Session, token: str, password: str, client: str) -> User:
    link = _valid_link(db, token, "reset", client)
    user = link.target_user
    if not user:
        raise NotFound("Аккаунт не найден")
    _claim(db, link)
    user.password_hash = hash_password(password)
    user.session_version += 1  # whoever still has the old password's sessions is signed out
    db.commit()
    return user


def _create_link(db: Session, *, purpose: str, created_by: User, ttl: timedelta, **fields) -> tuple[AccessLink, str]:
    token = new_link_token()
    link = AccessLink(purpose=purpose, token_hash=link_token_hash(token), created_by_id=created_by.id,
                      expires_at=utcnow() + ttl, **fields)
    db.add(link)
    db.commit()
    return link, token


def create_invite(db: Session, admin: User, note: Optional[str], role: Optional[str]) -> tuple[AccessLink, str]:
    return _create_link(db, purpose="invite", created_by=admin, ttl=timedelta(days=settings.invite_ttl_days),
                        note=(note or "").strip() or None, role=role)


def create_reset_link(db: Session, admin: User, user_id: uuid.UUID) -> tuple[AccessLink, str]:
    user = repo.by_id(db, user_id)
    if not user:
        raise NotFound("Аккаунт не найден")
    return _create_link(db, purpose="reset", created_by=admin, ttl=timedelta(hours=settings.reset_link_ttl_hours),
                        target_user_id=user.id, note=f"Сброс пароля для @{user.username}")


def list_links(db: Session) -> list[AccessLink]:
    return repo.all_links(db)


def revoke_link(db: Session, link_id: uuid.UUID) -> None:
    link = db.get(AccessLink, link_id)
    if not link:
        raise NotFound("Ссылка не найдена")
    if not link.used_at and not link.revoked_at:
        link.revoked_at = utcnow()
        db.commit()


# ---------------------------------------------------------------- profiles

def email_of(user: User) -> Optional[str]:
    return decrypt_email(user.email_encrypted)


def members(db: Session, role: Optional[str] = None, limit: int = 24) -> list[User]:
    return repo.visible_members(db, role=role, limit=min(max(limit, 1), 100))


def update_profile(db: Session, user: User, data: ProfileUpdate) -> User:
    values = data.model_dump(exclude_unset=True, mode="json")
    if "avatar_url" in values:
        check_url(user.username, values["avatar_url"], [user.avatar_url])
        if values["avatar_url"] != user.avatar_url:
            delete_own_url_after_commit(db, user.username, user.avatar_url)
    if "email" in values:
        email = values.pop("email")
        if email:
            if repo.email_taken(db, email, except_user=user.id):
                raise Conflict("Этот email уже привязан к другому аккаунту")
            user.email_hash, user.email_encrypted = email_index(email), encrypt_email(email)
        else:
            user.email_hash = user.email_encrypted = None
    if values.get("role") and values["role"] not in {r.value for r in Role}:
        raise Invalid("Неизвестная роль")
    if "hall" in values:
        hall = values["hall"] or {}
        old_cover = (user.hall or {}).get("cover_url")
        check_url(user.username, hall.get("cover_url"), [old_cover])
        if hall.get("cover_url") != old_cover:
            delete_own_url_after_commit(db, user.username, old_cover)
        values["hall"] = {k: v for k, v in hall.items() if v is not None}
    for field, value in values.items():
        setattr(user, field, value)
    db.commit()
    return user


def change_password(db: Session, user: User, current: str, new: str) -> User:
    if not verify_password(current, user.password_hash):
        raise Forbidden("Текущий пароль указан неверно")
    user.password_hash = hash_password(new)
    user.session_version += 1  # other devices are signed out
    db.commit()
    return user


def revoke_sessions(db: Session, user: User) -> User:
    user.session_version += 1
    db.commit()
    return user


# ---------------------------------------------------------------- administration

def all_users(db: Session) -> list[User]:
    return repo.all_users(db)


def admin_update_user(db: Session, admin: User, user_id: uuid.UUID, is_hidden: Optional[bool], is_admin: Optional[bool],
                      is_moderator: Optional[bool] = None) -> User:
    user = repo.by_id(db, user_id)
    if not user:
        raise NotFound("Аккаунт не найден")
    if user.id == admin.id and (is_hidden or is_admin is False):
        raise Invalid("Нельзя скрыть себя или снять с себя права администратора")
    if is_hidden is not None:
        user.is_hidden = is_hidden
    if is_admin is not None:
        user.is_admin = is_admin
    if is_moderator is not None:
        user.is_moderator = is_moderator
    db.commit()
    return user


def is_expired(link: AccessLink) -> bool:
    return aware(link.expires_at) <= utcnow()
