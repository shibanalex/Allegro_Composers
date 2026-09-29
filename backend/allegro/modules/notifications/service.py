"""Use cases of the notifications module.

Events come from the outbox (core.events), written by the modules that publish: «published» (a new work,
sketch, article, performance, blog post, news) and «removed». The worker hands each event to `handle`:

- «published» → one notification for every member but the author (one INSERT … SELECT, not a loop),
  then a push to the devices of those who want this kind of publication;
- «removed» → the notifications about it disappear.

E-mail goes as a digest (daily or weekly), never one letter per post: `send_digests`.

What a member wants is kept in `notification_settings`; no row means the defaults (every kind, push on,
no e-mail). The bell and the list show only the kinds a member chose.
"""
import html
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Uuid, delete, func, insert, literal, select, update
from sqlalchemy.orm import Session

from allegro.core.config import settings
from allegro.core.errors import Invalid
from allegro.core.mail import mail_enabled, send_mail
from allegro.modules.accounts.service import email_of, member_ids_except, user_by_id, visible_authors
from allegro.modules.notifications import push
from allegro.modules.notifications.models import Notification, NotificationSettings, PushSubscription
from allegro.modules.notifications.schemas import KINDS, NotificationOut, NotificationPage, SettingsIn, SettingsOut

log = logging.getLogger("allegro.notifications")

KIND_WORDS = {
    "opus": "новое сочинение", "sketch": "новый эскиз", "article": "новая статья", "performance": "новое исполнение",
    "note": "новая запись в блоге", "news": "новости сообщества", "workshop": "новая запись",
}
MAX_PUSHES_PER_EVENT = 5000


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def site_url() -> str:
    return (settings.public_url or settings.site_url or settings.render_external_url or "").rstrip("/")


# ---------------------------------------------------------------- settings

def _settings_row(db: Session, user_id: uuid.UUID) -> Optional[NotificationSettings]:
    return db.get(NotificationSettings, user_id)


def _kinds(row: Optional[NotificationSettings]) -> list[str]:
    return list(row.kinds) if row and row.kinds else list(KINDS)


def get_settings(db: Session, user) -> SettingsOut:
    row = _settings_row(db, user.id)
    return SettingsOut(
        kinds=_kinds(row), push=row.push if row else True, email=row.email if row else "off",
        email_available=mail_enabled() and bool(email_of(user)), push_key=push.public_key(),
    )


def update_settings(db: Session, user, data: SettingsIn) -> SettingsOut:
    row = _settings_row(db, user.id)
    if not row:
        row = NotificationSettings(user_id=user.id, kinds=[], push=True, email="off")
        db.add(row)
    values = data.model_dump(exclude_unset=True)
    if "kinds" in values:
        if not values["kinds"]:
            raise Invalid("Оставьте хотя бы один вид публикаций — или выключите уведомления в браузере")
        row.kinds = [] if set(values["kinds"]) == set(KINDS) else values["kinds"]
    if "push" in values:
        row.push = values["push"]
    if "email" in values:
        if values["email"] != "off" and not (mail_enabled() and email_of(user)):
            raise Invalid("Письма недоступны: укажите почту в «Оформить зал»" if mail_enabled() else "Сайт пока не отправляет письма")
        row.email = values["email"]
    db.commit()
    return get_settings(db, user)


# ---------------------------------------------------------------- the bell

def _visible(user_id: uuid.UUID, kinds: list[str]):
    return (Notification.user_id == user_id, Notification.kind.in_(kinds + (["workshop"] if "note" in kinds else [])),
            visible_authors(Notification.actor_id))


def unread_count(db: Session, user) -> int:
    kinds = _kinds(_settings_row(db, user.id))
    return db.scalar(select(func.count()).where(*_visible(user.id, kinds), Notification.read_at.is_(None))) or 0


def list_notifications(db: Session, user, before: Optional[int], limit: int) -> NotificationPage:
    kinds = _kinds(_settings_row(db, user.id))
    stmt = select(Notification).where(*_visible(user.id, kinds))
    if before:
        stmt = stmt.where(Notification.id < before)
    items = list(db.scalars(stmt.order_by(Notification.id.desc()).limit(limit)).unique())
    return NotificationPage(
        items=[NotificationOut.model_validate(n) for n in items],
        unread=unread_count(db, user),
        next_before=items[-1].id if len(items) == limit else None,
    )


def mark_read(db: Session, user, ids: Optional[list[int]]) -> int:
    stmt = update(Notification).where(Notification.user_id == user.id, Notification.read_at.is_(None))
    if ids is not None:
        stmt = stmt.where(Notification.id.in_(ids))
    db.execute(stmt.values(read_at=utcnow()))
    db.commit()
    return unread_count(db, user)


# ---------------------------------------------------------------- push subscriptions

def subscribe(db: Session, user, endpoint: str, p256dh: str, auth: str) -> None:
    if not push.allowed_endpoint(endpoint):
        raise Invalid("Неизвестный сервис уведомлений браузера")
    existing = db.scalar(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
    if existing:  # the same browser, maybe signed in as someone else now
        existing.user_id, existing.p256dh, existing.auth = user.id, p256dh, auth
    else:
        db.add(PushSubscription(user_id=user.id, endpoint=endpoint, p256dh=p256dh, auth=auth))
    db.commit()


def unsubscribe(db: Session, user, endpoint: str) -> None:
    db.execute(delete(PushSubscription).where(PushSubscription.endpoint == endpoint, PushSubscription.user_id == user.id))
    db.commit()


# ---------------------------------------------------------------- events from the outbox (the worker)

def handle(db: Session, kind: str, payload: dict) -> None:
    if kind == "published":
        _published(db, payload)
    elif kind == "removed":
        db.execute(delete(Notification).where(
            Notification.target_type == payload["target_type"], Notification.target_id == uuid.UUID(payload["id"]),
        ))
        db.commit()


def _published(db: Session, p: dict) -> None:
    author_id, target_id = uuid.UUID(p["author_id"]), uuid.UUID(p["id"])
    author = user_by_id(db, author_id)
    if not author or author.is_hidden:
        return
    already = db.scalar(select(func.count()).where(Notification.target_type == p["target_type"], Notification.target_id == target_id))
    if already:  # a retried event: the members were told already
        return
    title, url = str(p.get("title") or "")[:255], str(p.get("url") or "/")[:512]
    recipients = member_ids_except(author_id).subquery()
    now = utcnow()
    db.execute(insert(Notification).from_select(
        ["user_id", "actor_id", "kind", "target_type", "target_id", "title", "url", "created_at"],
        select(
            recipients.c.id, literal(author_id, Uuid), literal(p["kind"]), literal(p["target_type"]),
            literal(target_id, Uuid), literal(title), literal(url), literal(now),
        ),
    ))
    db.commit()
    _push_all(db, author, p["kind"], title, url)


def _push_all(db: Session, author, kind: str, title: str, url: str) -> None:
    """Every device of every member who wants this kind of publication by push"""
    rows = db.execute(
        select(PushSubscription, NotificationSettings)
        .join(NotificationSettings, NotificationSettings.user_id == PushSubscription.user_id, isouter=True)
        .where(PushSubscription.user_id != author.id).limit(MAX_PUSHES_PER_EVENT)
    ).all()
    message = {"title": f"{author.display_name} · {KIND_WORDS.get(kind, 'новая публикация')}", "body": title,
               "url": url, "tag": url}
    gone = []
    for sub, prefs in rows:
        if prefs and (not prefs.push or kind not in _kinds(prefs) and not (kind == "workshop" and "note" in _kinds(prefs))):
            continue
        try:
            push.send(sub.endpoint, sub.p256dh, sub.auth, message)
        except push.Gone:
            gone.append(sub.id)
        except Exception as e:  # one browser's trouble must not stop the others
            log.warning("push to %s failed: %s", sub.endpoint[:60], e)
    if gone:
        db.execute(delete(PushSubscription).where(PushSubscription.id.in_(gone)))
        db.commit()


# ---------------------------------------------------------------- e-mail digests

DIGEST_HOUR = 9  # Moscow time
PERIODS = {"daily": timedelta(days=1), "weekly": timedelta(days=7)}


def send_digests(db: Session, now: Optional[datetime] = None) -> int:
    """Letters to those whose day (or week) has come: what was published since the last letter"""
    if not mail_enabled():
        return 0
    now = now or utcnow()
    moscow = now + timedelta(hours=3)
    if moscow.hour < DIGEST_HOUR:
        return 0
    sent = 0
    for row in db.scalars(select(NotificationSettings).where(NotificationSettings.email.in_(PERIODS))):
        since = row.last_digest_at or (now - PERIODS[row.email])
        if since.tzinfo is None:
            since = since.replace(tzinfo=timezone.utc)
        if now - since < PERIODS[row.email] - timedelta(hours=1):
            continue
        user = user_by_id(db, row.user_id)
        address = email_of(user) if user and not user.is_hidden else None
        if not address:
            continue
        items = list(db.scalars(
            select(Notification).where(*_visible(user.id, _kinds(row)), Notification.created_at > since)
            .order_by(Notification.created_at.desc()).limit(50)
        ).unique())
        row.last_digest_at = now
        db.commit()
        if not items:
            continue
        try:
            send_mail(address, *_digest(items, row.email))
            sent += 1
        except Exception as e:
            log.warning("digest to user %s failed: %s", user.id, e)
    return sent


def _digest(items: list[Notification], period: str) -> tuple[str, str, str]:
    base = site_url()
    when = "за день" if period == "daily" else "за неделю"
    subject = f"Allegro: {len(items)} новых публикаций {when}"
    lines = [f"— {n.actor.display_name if n.actor else 'Участник'}: {KIND_WORDS.get(n.kind, 'публикация')} «{n.title}» {base}{n.url}"
             for n in items]
    settings_link = f"{base}/notifications"
    text = f"Что нового в Allegro {when}:\n\n" + "\n".join(lines) + f"\n\nНастроить или отключить письма: {settings_link}\n"
    rows = "".join(
        f'<li style="margin:0 0 10px"><b>{html.escape(n.actor.display_name if n.actor else "Участник")}</b> · '
        f'{html.escape(KIND_WORDS.get(n.kind, "публикация"))}<br>'
        f'<a href="{html.escape(base + n.url)}" style="color:#9c7a45">{html.escape(n.title)}</a></li>'
        for n in items
    )
    body = (f'<div style="font-family:Georgia,serif;color:#222"><h2 style="font-weight:normal">Что нового в Allegro {when}</h2>'
            f'<ul style="padding-left:18px">{rows}</ul>'
            f'<p style="color:#777;font-size:13px"><a href="{html.escape(settings_link)}" style="color:#777">Настроить или отключить письма</a></p></div>')
    return subject, text, body
