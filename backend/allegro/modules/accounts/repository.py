"""Queries of the accounts module (no commits here: transactions belong to the service)"""
import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from allegro.core.security import email_index, link_token_hash
from allegro.modules.accounts.models import AccessLink, User


def by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.get(User, user_id)


def by_username(db: Session, username: str, *, visible_only: bool = False) -> Optional[User]:
    stmt = select(User).where(User.username == username.strip().lower())
    if visible_only:
        stmt = stmt.where(User.is_hidden.is_(False))
    return db.scalar(stmt)


def by_login(db: Session, login: str) -> Optional[User]:
    """Username or e-mail (looked up through its keyed hash)"""
    value = login.strip().lower()
    return db.scalar(select(User).where(or_(User.username == value, User.email_hash == email_index(value))))


def username_taken(db: Session, username: str) -> bool:
    return db.scalar(select(User.id).where(User.username == username)) is not None


def email_taken(db: Session, email: str, *, except_user: Optional[uuid.UUID] = None) -> bool:
    stmt = select(User.id).where(User.email_hash == email_index(email))
    if except_user:
        stmt = stmt.where(User.id != except_user)
    return db.scalar(stmt) is not None


def count_users(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User)) or 0


def visible_members(db: Session, *, role: Optional[str] = None, where=None, limit: int = 24, offset: int = 0) -> tuple[list[User], int]:
    """A page of members who are not in the shadow, the newest first, and how many there are in all"""
    stmt = select(User).where(User.is_hidden.is_(False))
    if role:
        stmt = stmt.where(User.role == role)
    if where is not None:
        stmt = stmt.where(where)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    users = list(db.scalars(stmt.order_by(User.created_at.desc(), User.id).limit(limit).offset(offset)))
    return users, total


def all_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at)))


def visible_user_ids():
    """Subquery of members who are not in the shadow"""
    return select(User.id).where(User.is_hidden.is_(False))


def link_by_token(db: Session, token: str) -> Optional[AccessLink]:
    return db.scalar(select(AccessLink).where(AccessLink.token_hash == link_token_hash(token)))


