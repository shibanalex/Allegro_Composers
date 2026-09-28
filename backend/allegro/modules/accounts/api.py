"""HTTP layer of the accounts module: parse, call a use case, shape the answer — no business rules here"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from allegro.core.db import get_db
from allegro.core.errors import NotFound
from allegro.core.security import create_access_token
from allegro.modules.accounts import service
from allegro.modules.accounts.deps import client_address, get_admin, get_current_user
from allegro.modules.accounts.models import AccessLink, User
from allegro.modules.accounts.roles import capabilities_of
from allegro.modules.accounts.schemas import (
    AccessLinkOut, AdminUserOut, AdminUserUpdate, InviteIn, LinkCheckOut, LoginIn, MeOut, PasswordChangeIn,
    ProfileOut, ProfileUpdate, RegisterIn, ResetIn, SetupIn, SiteConfig, TokenOut,
)

router = APIRouter(tags=["accounts"])


def _profile(db: Session, user: User) -> ProfileOut:
    return ProfileOut.model_validate(user).model_copy(update={"stats": service.stats_for(db, [user.id])[user.id]})


def _me(db: Session, user: User) -> MeOut:
    profile = _profile(db, user)
    return MeOut(
        **profile.model_dump(), email=service.email_of(user), is_admin=user.is_admin,
        capabilities=sorted(c.value for c in capabilities_of(user.role, user.is_admin)),
    )


def _token(db: Session, user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id), user=_me(db, user))


def _link_out(link: AccessLink, token: Optional[str] = None) -> AccessLinkOut:
    return AccessLinkOut.model_validate(link).model_copy(update={"token": token, "status": link.status})


# ---------------------------------------------------------------- joining and signing in

@router.get("/api/auth/config", response_model=SiteConfig)
def site_config(db: Session = Depends(get_db)):
    """What the site offers: sign-up mode, first-start setup, roles and hall styles"""
    return service.site_config(db)


@router.post("/api/auth/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, request: Request, db: Session = Depends(get_db)):
    return _token(db, service.register(db, data, client_address(request)))


@router.post("/api/auth/setup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def first_setup(data: SetupIn, request: Request, db: Session = Depends(get_db)):
    """The very first account of a fresh site, created with the SETUP_TOKEN code from the hosting settings.
    Once any account exists this is closed for good."""
    return _token(db, service.setup(db, data, client_address(request)))


@router.post("/api/auth/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    return _token(db, service.login(db, data.login, data.password, client_address(request)))


@router.get("/api/auth/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _me(db, user)


@router.get("/api/auth/links/{token}", response_model=LinkCheckOut)
def check_link(token: str, db: Session = Depends(get_db)):
    """Is this invitation / reset link still usable (the sign-up and reset pages ask before showing the form)"""
    return service.check_link(db, token)


@router.post("/api/auth/reset", response_model=TokenOut)
def reset_password(data: ResetIn, request: Request, db: Session = Depends(get_db)):
    return _token(db, service.reset_password(db, data.token, data.password, client_address(request)))


# ---------------------------------------------------------------- profiles

@router.get("/api/users", response_model=list[ProfileOut])
def list_members(role: Optional[str] = None, limit: int = 24, db: Session = Depends(get_db)):
    """Members' halls for the main page: the earliest members first"""
    users = service.members(db, role, limit)
    stats = service.stats_for(db, [u.id for u in users])
    return [ProfileOut.model_validate(u).model_copy(update={"stats": stats[u.id]}) for u in users]


@router.patch("/api/users/me", response_model=MeOut)
def update_me(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _me(db, service.update_profile(db, user, data))


@router.post("/api/users/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(data: PasswordChangeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service.change_password(db, user, data.current_password, data.new_password)


@router.get("/api/users/{username}", response_model=ProfileOut)
def get_profile(username: str, db: Session = Depends(get_db)):
    user = service.get_visible_user(db, username)
    if not user:
        raise NotFound("Автор не найден")
    return _profile(db, user)


# ---------------------------------------------------------------- administration

@router.get("/api/admin/links", response_model=list[AccessLinkOut])
def list_links(_: User = Depends(get_admin), db: Session = Depends(get_db)):
    return [_link_out(link) for link in service.list_links(db)]


@router.post("/api/admin/invites", response_model=AccessLinkOut, status_code=status.HTTP_201_CREATED)
def create_invite(data: InviteIn, admin: User = Depends(get_admin), db: Session = Depends(get_db)):
    link, token = service.create_invite(db, admin, data.note, data.role)
    return _link_out(link, token)


@router.delete("/api/admin/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_link(link_id: uuid.UUID, _: User = Depends(get_admin), db: Session = Depends(get_db)):
    service.revoke_link(db, link_id)


@router.get("/api/admin/users", response_model=list[AdminUserOut])
def admin_users(_: User = Depends(get_admin), db: Session = Depends(get_db)):
    return [
        AdminUserOut.model_validate(u).model_copy(update={"has_email": bool(u.email_hash)})
        for u in service.all_users(db)
    ]


@router.patch("/api/admin/users/{user_id}", response_model=AdminUserOut)
def admin_update_user(user_id: uuid.UUID, data: AdminUserUpdate, admin: User = Depends(get_admin), db: Session = Depends(get_db)):
    user = service.admin_update_user(db, admin, user_id, data.is_hidden, data.is_admin)
    return AdminUserOut.model_validate(user).model_copy(update={"has_email": bool(user.email_hash)})


@router.post("/api/admin/users/{user_id}/reset-link", response_model=AccessLinkOut, status_code=status.HTTP_201_CREATED)
def reset_link(user_id: uuid.UUID, admin: User = Depends(get_admin), db: Session = Depends(get_db)):
    """A member forgot their password: a one-time link to set a new one (e-mail is optional, so no letters)"""
    link, token = service.create_reset_link(db, admin, user_id)
    return _link_out(link, token)
