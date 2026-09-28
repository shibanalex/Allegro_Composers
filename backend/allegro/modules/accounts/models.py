"""Tables owned by the accounts module"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from allegro.core.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    # E-mail is optional and never stored in the clear: a keyed hash to find the account, the address encrypted
    email_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True, index=True)
    email_encrypted: Mapped[Optional[str]] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    pseudonym: Mapped[Optional[str]] = mapped_column(String(120))
    bio: Mapped[Optional[str]] = mapped_column(String(400))  # short manifesto shown in the hall header
    about_md: Mapped[Optional[str]] = mapped_column(Text)  # full biography / CV
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512))
    links: Mapped[list] = mapped_column(JSON, default=list)  # [{label, url}]
    role: Mapped[str] = mapped_column(String(20), default="listener", server_default="listener", index=True)  # roles.Role
    hall_theme: Mapped[str] = mapped_column(String(20), default="romantic", server_default="romantic")  # roles.HALL_THEMES
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    # "In the shadow": the account and everything it made are hidden from the site, but kept in the database
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0", index=True)
    invited_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AccessLink(Base):
    """A one-time link: an invitation to join, or a password reset for an existing member.

    Only a hash of the link's secret is stored; the link itself is shown once, to the administrator who made it.
    """
    __tablename__ = "access_links"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    purpose: Mapped[str] = mapped_column(String(20), index=True)  # invite | reset
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    note: Mapped[Optional[str]] = mapped_column(String(200))  # whom it is for, as a reminder
    role: Mapped[Optional[str]] = mapped_column(String(20))  # invite: role suggested on the sign-up form
    target_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))  # reset
    used_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))  # invite
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    used_by: Mapped[Optional[User]] = relationship(foreign_keys=[used_by_id], lazy="joined")
    target_user: Mapped[Optional[User]] = relationship(foreign_keys=[target_user_id], lazy="joined")
    created_by: Mapped[Optional[User]] = relationship(foreign_keys=[created_by_id], lazy="joined")

    @property
    def status(self) -> str:
        if self.revoked_at:
            return "revoked"
        if self.used_at:
            return "used"
        return "expired" if aware(self.expires_at) <= utcnow() else "active"


def aware(value: datetime) -> datetime:
    """SQLite gives back naive datetimes; every stored time is UTC"""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
