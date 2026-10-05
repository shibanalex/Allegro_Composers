"""HTTP layer of the accounts module: parse, call a use case, shape the answer — no business rules here"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from allegro.core.db import get_db
from allegro.core.errors import NotFound
from allegro.core.security import create_access_token
from allegro.modules.accounts import service
from allegro.modules.accounts.deps import (
    clear_login_cookie, client_address, get_admin, get_current_user, set_login_cookie,
)
from allegro.modules.accounts.models import AccessLink, User
from allegro.modules.accounts.roles import matrix, user_capabilities
from allegro.modules.accounts.schemas import (
    AccessLinkOut, AdminUserOut, AdminUserUpdate, HintsIn, MemberPage, LinkCheckOut, LoginIn, MeOut, PasswordChangeIn,
    ProfileOut, ProfileUpdate, RegisterIn, ResetIn, SetupIn, SiteConfig, TokenOut, UsernameCheck,
)

router = APIRouter(tags=["accounts"])


def _profile(db: Session, user: User) -> ProfileOut:
    return ProfileOut.model_validate(user).model_copy(update={"stats": service.stats_for(db, [user.id])[user.id]})


def _me(db: Session, user: User) -> MeOut:
    profile = _profile(db, user)
    return MeOut(
        **profile.model_dump(), email=service.email_of(user), is_admin=user.is_admin, is_moderator=user.is_moderator,
        seen_hints=user.seen_hints or [],
        capabilities=sorted(c.value for c in user_capabilities(user)),
    )


def _token(db: Session, user: User, request: Request, response: Response) -> TokenOut:
    set_login_cookie(request, response, create_access_token(user.id, user.session_version))
    return TokenOut(user=_me(db, user))


def _link_out(link: AccessLink, token: Optional[str] = None) -> AccessLinkOut:
    return AccessLinkOut.model_validate(link).model_copy(update={"token": token, "status": link.status})


# ---------------------------------------------------------------- joining and signing in

@router.get("/api/auth/username", response_model=UsernameCheck)
def check_username(value: str = Query("", max_length=64), db: Session = Depends(get_db)):
    """Is this hall address usable and free? (the sign-up form asks as it is typed)"""
    return service.check_username(db, value)


@router.get("/api/auth/config", response_model=SiteConfig)
def site_config(db: Session = Depends(get_db)):
    """What the site offers: first-start setup, roles and hall styles"""
    return service.site_config(db)


@router.post("/api/auth/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    return _token(db, service.register(db, data, client_address(request)), request, response)


@router.post("/api/auth/setup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def first_setup(data: SetupIn, request: Request, response: Response, db: Session = Depends(get_db)):
    """The very first account of a fresh site, created with the SETUP_TOKEN code from the hosting settings.
    Once any account exists this is closed for good."""
    return _token(db, service.setup(db, data, client_address(request)), request, response)


@router.post("/api/auth/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    return _token(db, service.login(db, data.login, data.password, client_address(request)), request, response)


@router.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    """Signing out of this browser: the login cookie is removed"""
    clear_login_cookie(response)


@router.get("/api/auth/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _me(db, user)


@router.get("/api/auth/links/{token}", response_model=LinkCheckOut)
def check_link(token: str, db: Session = Depends(get_db)):
    """Is this invitation / reset link still usable (the sign-up and reset pages ask before showing the form)"""
    return service.check_link(db, token)


@router.post("/api/auth/reset", response_model=TokenOut)
def reset_password(data: ResetIn, request: Request, response: Response, db: Session = Depends(get_db)):
    return _token(db, service.reset_password(db, data.token, data.password, client_address(request)), request, response)


# ---------------------------------------------------------------- profiles

@router.get("/api/users", response_model=MemberPage)
def list_members(role: Optional[str] = None, q: str = Query("", max_length=100), limit: int = 24, offset: int = 0,
                 db: Session = Depends(get_db)):
    """The members: the newest first, by role and by name; with what each has published"""
    users, total = service.members(db, role, q, limit, offset)
    stats = service.stats_for(db, [u.id for u in users])
    return MemberPage(items=[ProfileOut.model_validate(u).model_copy(update={"stats": stats[u.id]}) for u in users], total=total)


@router.patch("/api/users/me", response_model=MeOut)
def update_me(data: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _me(db, service.update_profile(db, user, data))


@router.post("/api/users/me/hints", status_code=status.HTTP_204_NO_CONTENT)
def hints_seen(body: HintsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Onboarding hints were read (one, or all at once by «Больше не показывать»): they won't be shown again"""
    service.hints_seen(db, user, body.hints)


@router.delete("/api/users/me/hints", status_code=status.HTTP_204_NO_CONTENT)
def hints_again(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """«Показать подсказки снова»"""
    service.hints_again(db, user)


@router.post("/api/users/me/password", response_model=TokenOut)
def change_password(data: PasswordChangeIn, request: Request, response: Response, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    """A new password signs out every other device; this one gets a fresh token"""
    return _token(db, service.change_password(db, user, data.current_password, data.new_password), request, response)


@router.post("/api/users/me/sessions/revoke", response_model=TokenOut)
def sign_out_everywhere(request: Request, response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """«Выйти на всех устройствах»: every other login stops working; this one gets a fresh token"""
    return _token(db, service.revoke_sessions(db, user), request, response)


@router.get("/api/users/{username}", response_model=ProfileOut)
def get_profile(username: str, db: Session = Depends(get_db)):
    user = service.get_visible_user(db, username)
    if not user:
        raise NotFound("Автор не найден")
    return _profile(db, user)


# ---------------------------------------------------------------- administration

@router.get("/api/roles")
def roles_matrix():
    """Who may do what: every capability and the roles and staff levels that have it"""
    return matrix()


@router.get("/api/admin/users", response_model=list[AdminUserOut])
def admin_users(_: User = Depends(get_admin), db: Session = Depends(get_db)):
    return [
        AdminUserOut.model_validate(u).model_copy(update={"has_email": bool(u.email_hash)})
        for u in service.all_users(db)
    ]


@router.patch("/api/admin/users/{user_id}", response_model=AdminUserOut)
def admin_update_user(user_id: uuid.UUID, data: AdminUserUpdate, admin: User = Depends(get_admin), db: Session = Depends(get_db)):
    user = service.admin_update_user(db, admin, user_id, data.is_hidden, data.is_admin, data.is_moderator)
    return AdminUserOut.model_validate(user).model_copy(update={"has_email": bool(user.email_hash)})


@router.post("/api/admin/users/{user_id}/reset-link", response_model=AccessLinkOut, status_code=status.HTTP_201_CREATED)
def reset_link(user_id: uuid.UUID, admin: User = Depends(get_admin), db: Session = Depends(get_db)):
    """A member forgot their password: a one-time link to set a new one (e-mail is optional, so no letters)"""
    link, token = service.create_reset_link(db, admin, user_id)
    return _link_out(link, token)
