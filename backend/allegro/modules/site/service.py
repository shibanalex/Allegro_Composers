"""Use cases of the site module: «О нас» / «Ссылки» pages and members' suggestions"""
import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from allegro.core.errors import Forbidden, NotFound
from allegro.core.ratelimit import AttemptLimiter
from allegro.modules.accounts.roles import Capability, can
from allegro.modules.accounts.service import visible_authors
from allegro.modules.site.models import Feedback, SitePage, utcnow
from allegro.modules.site.schemas import FeedbackIn, FeedbackUpdate

# Shown until an administrator writes their own text
DEFAULT_PAGES = {
    "about": (
        "## Allegro\n\n"
        "Сообщество композиторов, теоретиков, исполнителей и слушателей.\n\n"
        "Композиторы выставляют сочинения с партитурами и записями, теоретики пишут статьи и обзоры, "
        "исполнители делятся исполнениями, а все вместе ведут блоги и обсуждают музыку."
    ),
    "links": "",
}

# Suggestions: a handful a day per member is plenty; more is a flood
feedback_limiter = AttemptLimiter(10, 24 * 60 * 60, "Слишком много предложений за сутки.")


def get_page(db: Session, slug: str) -> dict:
    page = db.get(SitePage, slug)
    if page:
        return {"slug": slug, "content_md": page.content_md, "updated_at": page.updated_at}
    return {"slug": slug, "content_md": DEFAULT_PAGES.get(slug, ""), "updated_at": None}


def put_page(db: Session, admin, slug: str, content_md: str) -> dict:
    page = db.get(SitePage, slug)
    if page:
        page.content_md, page.updated_by_id = content_md, admin.id
    else:
        db.add(SitePage(slug=slug, content_md=content_md, updated_by_id=admin.id))
    db.commit()
    return get_page(db, slug)


def list_feedback(db: Session, status: Optional[str], limit: int, offset: int) -> tuple[list[Feedback], int]:
    stmt = select(Feedback).where(visible_authors(Feedback.author_id))
    if status:
        stmt = stmt.where(Feedback.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = list(db.scalars(stmt.order_by(Feedback.created_at.desc()).offset(offset).limit(limit)).unique())
    return items, total


def create_feedback(db: Session, user, data: FeedbackIn) -> Feedback:
    feedback_limiter.check((user.id,))
    feedback_limiter.hit((user.id,))
    item = Feedback(author_id=user.id, kind=data.kind, title=data.title.strip(), body=data.body.strip())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_feedback(db: Session, feedback_id: uuid.UUID, data: FeedbackUpdate) -> Feedback:
    """Administrators set the status and answer"""
    item = db.get(Feedback, feedback_id)
    if not item:
        raise NotFound("Предложение не найдено")
    values = data.model_dump(exclude_unset=True)
    if "status" in values:
        item.status = values["status"]
    if "reply_md" in values:
        item.reply_md = (values["reply_md"] or "").strip() or None
        item.replied_at = utcnow() if item.reply_md else None
    db.commit()
    return item


def delete_feedback(db: Session, user, feedback_id: uuid.UUID) -> None:
    """The author may take back a suggestion nobody has answered yet; administrators may remove any"""
    item = db.get(Feedback, feedback_id)
    if not item:
        raise NotFound("Предложение не найдено")
    if not can(user, Capability.MANAGE_SITE) and (item.author_id != user.id or item.status != "new" or item.reply_md):
        raise Forbidden("Удалить можно только своё предложение, пока на него не ответили")
    db.delete(item)
    db.commit()
