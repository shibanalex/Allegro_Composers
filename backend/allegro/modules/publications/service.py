"""Use cases of the publications module: blog posts, articles, news, members' materials.

Public API for other modules: `posts_out`, `recent_posts`, `resolve_post_target`, `search_posts`, `count_posts`,
`count_articles`.

Posts refer to each other in two ways: a *quotation* (`quote_post_id`, a repost with one's own words) and
*links* in the text (…/posts/<slug>, …/opus/<slug>), stored in `post_links` when the post is saved, so the
linked post or work can list its mentions without reading anyone's texts.
"""
import re
import uuid
from typing import Optional

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from allegro.core import textsearch
from allegro.core.events import emit
from allegro.core.errors import Forbidden, Invalid, NotFound, Unauthorized
from allegro.core.files import check_url, delete_own_url_after_commit
from allegro.core.slugs import unique_slug
from allegro.modules.accounts.roles import CAPABILITY_REFUSALS, Capability, can
from allegro.modules.accounts.service import author_named, get_visible_user, visible_authors
from allegro.modules.catalog.service import opus_brief, opus_id_by_slug, published_opus_ids, visible_published_opus
from allegro.modules.discussion.schemas import ReactionsOut
from allegro.modules.discussion.service import Target, count_comments, forget_target, reaction_summary
from allegro.modules.publications.models import Material, Post, PostLink
from allegro.modules.publications.schemas import (
    MaterialFields, MaterialIn, PostBrief, PostCreate, PostFields, PostOut,
)

# What each kind of publication takes (roles.py)
KIND_CAPABILITY = {
    "note": Capability.PUBLISH_NOTE, "sketch": Capability.PUBLISH_SKETCH,
    "article": Capability.PUBLISH_ARTICLE, "news": Capability.PUBLISH_NEWS,
    "workshop": Capability.PUBLISH_NOTE,
}
# Links to posts and works in a text: relative or with any host (…/posts/<slug>, …/opus/<slug>)
LINK = re.compile(r"/(posts|opus)/([A-Za-z0-9_-]{1,255})")
MAX_LINKS = 50


# ---------------------------------------------------------------- shaping answers

def post_brief(post: Optional[Post]) -> Optional[PostBrief]:
    """None for drafts and posts of shadowed authors"""
    if not post or post.status == "draft" or post.author.is_hidden:
        return None
    images = [a.get("url") for a in post.attachments or [] if (a.get("content_type") or "").startswith("image/")]
    text = " ".join(re.sub(r"[#*_>`\[\]()!]", " ", post.content_md or "").split())
    return PostBrief.model_validate(post).model_copy(update={
        "preview": text[:300] + ("…" if len(text) > 300 else ""),
        "image_url": post.cover_url or (images[0] if images else None),
    })


def posts_out(db: Session, posts: list[Post]) -> list[PostOut]:
    counts = count_comments(db, "post", [p.id for p in posts])
    return [
        PostOut.model_validate(p).model_copy(update={
            "opus": opus_brief(p.opus), "quote": post_brief(p.quote), "comment_count": counts.get(p.id, 0),
        })
        for p in posts
    ]


# ---------------------------------------------------------------- posts

def _get_post(db: Session, slug: str, user) -> Post:
    post = db.scalar(select(Post).where(Post.slug == slug, visible_authors(Post.author_id)))
    if not post or (post.status == "draft" and (not user or user.id != post.author_id)):
        raise NotFound("Публикация не найдена")
    return post


def _own_post(db: Session, slug: str, user) -> Post:
    post = _get_post(db, slug, user)
    if post.author_id != user.id:
        raise Forbidden("Это не ваша публикация")
    return post


def _check_kind(user, kind: str) -> None:
    capability = KIND_CAPABILITY.get(kind)
    if capability and not can(user, capability):
        raise Forbidden(CAPABILITY_REFUSALS[capability])


def _check_text(kind: str, title: str, content: str, attachments: list, refers: bool = False) -> None:
    """Articles, news and workshop threads need a title; a blog post is like a channel message: text or media is enough"""
    if kind != "note" and not title.strip():
        raise Invalid("Нужен заголовок")
    if not content.strip() and not attachments and not refers:  # a quotation or a shared work is content too
        raise Invalid("Пустая запись")


def _check_files(user, values: dict, post: Optional[Post] = None) -> None:
    """Cover and attachments must be the author's own uploads (or already on this post)"""
    current = [post.cover_url, *(a.get("url") for a in post.attachments or [])] if post else []
    if "cover_url" in values:
        check_url(user.username, values["cover_url"], current)
    for attachment in values.get("attachments") or []:
        check_url(user.username, attachment["url"], current)


SKETCH_TITLE = 120


def _check_sketch(post_kind: str, title: str, attachments: list, values: dict) -> None:
    """A sketch is one recording with a short title; the «ищу отзыв» flag belongs to sketches only"""
    if post_kind != "sketch":
        values.pop("seeking_feedback", None)
        return
    audio = [a for a in attachments if (a.get("content_type") or "").startswith("audio/")]
    if len(audio) != 1 or len(attachments) != 1:
        raise Invalid("В эскизе — одна запись: голосом или файлом")
    if len(title.strip()) > SKETCH_TITLE:
        raise Invalid(f"Название эскиза — не длиннее {SKETCH_TITLE} знаков")


def _check_quote(db: Session, quote_id: Optional[uuid.UUID], post: Optional[Post] = None) -> None:
    if not quote_id:
        return
    quoted = db.get(Post, quote_id)
    if not post_brief(quoted) or (post and quoted.id == post.id):
        raise Invalid("Цитируемая запись не найдена")


def _save_links(db: Session, post: Post) -> None:
    """Which posts and works the text links to (replaces what was there)"""
    found: dict[str, list[str]] = {"posts": [], "opus": []}
    for where, slug in LINK.findall(post.content_md or "")[:MAX_LINKS]:
        found[where].append(slug)
    targets = {("opus", i) for i in published_opus_ids(db, found["opus"]).values()}
    if found["posts"]:
        targets |= {("post", i) for i in db.scalars(select(Post.id).where(
            Post.slug.in_(found["posts"]), Post.status != "draft", visible_authors(Post.author_id),
        )) if i != post.id}
    db.execute(delete(PostLink).where(PostLink.post_id == post.id))
    db.add_all(PostLink(post_id=post.id, target_kind=kind, target_id=target_id) for kind, target_id in targets)


def mentions(db: Session, kind: str, slug: str, limit: int = 20) -> list[PostBrief]:
    """Published posts whose text links to this post or work, newest first"""
    if kind == "post":
        target = db.scalar(select(Post.id).where(Post.slug == slug))
    else:
        target = opus_id_by_slug(db, slug)
    if not target:
        raise NotFound("Не найдено")
    posts = db.scalars(
        select(Post).join(PostLink, PostLink.post_id == Post.id)
        .where(PostLink.target_kind == kind, PostLink.target_id == target, Post.status == "published",
               visible_authors(Post.author_id))
        .order_by(Post.created_at.desc()).limit(limit)
    ).unique()
    return [b for b in (post_brief(p) for p in posts) if b]


def _announce(db: Session, post: Post) -> None:
    """A post just became public: the notifications will tell the members (core.events)"""
    text = post.title or " ".join(re.sub(r"[#*_>`\[\]()!]", " ", post.content_md or "").split())[:80]
    emit(db, "published", target_type="post", kind=post.kind, id=post.id, author_id=post.author_id,
         title=text or "запись", url=f"/posts/{post.slug}")


def _slug_source(title: str, content: str) -> str:
    return title.strip() or " ".join(content.split()[:6]) or "zapis"


def list_posts(db: Session, user, *, kinds: Optional[list[str]] = None, author: Optional[str] = None,
               opus: Optional[str] = None, mine: bool = False, limit: int = 20, offset: int = 0) -> tuple[list[Post], int]:
    stmt = select(Post)
    if mine:
        if not user:
            raise Unauthorized("Требуется вход")
        stmt = stmt.where(Post.author_id == user.id)
    else:
        stmt = stmt.where(Post.status == "published", visible_authors(Post.author_id))
    if kinds:
        stmt = stmt.where(Post.kind.in_(kinds))
    if author:
        stmt = stmt.where(author_named(Post.author_id, author))
    if opus:
        stmt = stmt.where(Post.opus_id == opus_id_by_slug(db, opus))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    posts = list(db.scalars(stmt.order_by(Post.created_at.desc()).offset(offset).limit(limit)).unique())
    return posts, total


def post_page(db: Session, slug: str, user) -> PostOut:
    post = read_post(db, slug, user)
    likes = reaction_summary(db, "post", [post.id], user)[post.id]
    # this view is counted after the answer (count_view): the number shown already includes it
    return posts_out(db, [post])[0].model_copy(update={
        "likes": ReactionsOut(count=likes.count, mine=likes.mine), "view_count": post.view_count + 1,
    })


def read_post(db: Session, slug: str, user) -> Post:
    return _get_post(db, slug, user)


def count_view(post_id: uuid.UUID) -> None:
    """One more view — after the answer has gone (a background task): the reader never waits for it"""
    from allegro.core.db import SessionLocal

    with SessionLocal() as db:
        db.execute(update(Post).where(Post.id == post_id).values(view_count=Post.view_count + 1))
        db.commit()


def create_post(db: Session, user, data: PostCreate) -> Post:
    _check_kind(user, data.kind)
    _check_text(data.kind, data.title, data.content_md, data.attachments or [], bool(data.quote_post_id or data.opus_id))
    visible_published_opus(db, data.opus_id)
    _check_quote(db, data.quote_post_id)
    values = data.model_dump(exclude_none=True, mode="json")
    _check_files(user, values)
    _check_sketch(data.kind, data.title, values.get("attachments") or [], values)
    values["title"] = data.title.strip()
    if data.opus_id:
        values["opus_id"] = data.opus_id
    if data.quote_post_id:
        values["quote_post_id"] = data.quote_post_id
    post = Post(author_id=user.id, slug=unique_slug(db, Post.slug, _slug_source(data.title, data.content_md)), **values)
    db.add(post)
    db.flush()
    _save_links(db, post)
    if post.status == "published":
        _announce(db, post)
    db.commit()
    return post


def update_post(db: Session, user, slug: str, data: PostFields) -> Post:
    post = _own_post(db, slug, user)
    was_public = post.status == "published"
    values = data.model_dump(exclude_unset=True, mode="json")
    if "kind" in values and values["kind"] != post.kind:
        _check_kind(user, values["kind"])
    _check_files(user, values, post)
    if "opus_id" in values:
        visible_published_opus(db, data.opus_id)
        values["opus_id"] = data.opus_id
    if "quote_post_id" in values:
        _check_quote(db, data.quote_post_id, post)
        values["quote_post_id"] = data.quote_post_id
    if "cover_url" in values and values["cover_url"] != post.cover_url:
        delete_own_url_after_commit(db, user.username, post.cover_url)
    for field, value in values.items():
        setattr(post, field, value)
    _check_text(post.kind, post.title or "", post.content_md or "", post.attachments or [], bool(post.quote_post_id or post.opus_id))
    _check_sketch(post.kind, post.title or "", post.attachments or [], values)
    if post.kind != "sketch":
        post.seeking_feedback = False
    if "content_md" in values:
        _save_links(db, post)
    if post.status == "published" and not was_public:  # a draft published at last
        _announce(db, post)
    db.commit()
    return post


def delete_post(db: Session, user, slug: str) -> None:
    """The author, or a moderator (their files are then left in storage: only the owner's are ever removed)"""
    post = _get_post(db, slug, user)
    if post.author_id != user.id and not can(user, Capability.MODERATE):
        raise Forbidden("Это не ваша публикация")
    delete_own_url_after_commit(db, user.username, post.cover_url)
    for attachment in post.attachments or []:
        delete_own_url_after_commit(db, user.username, attachment.get("url"))
    forget_target(db, "post", post.id)
    emit(db, "removed", target_type="post", id=post.id)
    db.delete(post)
    db.commit()


# ---------------------------------------------------------------- materials

def list_materials(db: Session, author: str) -> list[Material]:
    owner = get_visible_user(db, author)
    if not owner:
        raise NotFound("Автор не найден")
    return list(db.scalars(
        select(Material).where(Material.author_id == owner.id).order_by(Material.position, Material.created_at.desc())
    ))


def _check_material(kind: str, url: Optional[str], file: Optional[dict]) -> None:
    if kind == "link" and not url:
        raise Invalid("Для ссылки нужен адрес")
    if kind == "file" and not file:
        raise Invalid("Прикрепите файл")
    # a book may be a file, a link to a shop/library, or just a recommendation with a description


def _check_material_files(user, values: dict, material: Optional[Material] = None) -> None:
    current = [material.cover_url, (material.file or {}).get("url")] if material else []
    if values.get("file"):
        check_url(user.username, values["file"]["url"], current)
    if "cover_url" in values:
        check_url(user.username, values["cover_url"], current)


def _own_material(db: Session, material_id: uuid.UUID, user) -> Material:
    material = db.get(Material, material_id)
    if not material or material.author_id != user.id:
        raise NotFound("Материал не найден")
    return material


def create_material(db: Session, user, data: MaterialIn) -> Material:
    if not can(user, Capability.SHARE_MATERIAL):
        raise Forbidden(CAPABILITY_REFUSALS[Capability.SHARE_MATERIAL])
    values = data.model_dump(exclude_none=True, mode="json")
    _check_material_files(user, values)
    _check_material(data.kind, values.get("url"), values.get("file"))
    material = Material(author_id=user.id, **values)
    db.add(material)
    db.commit()
    return material


def update_material(db: Session, user, material_id: uuid.UUID, data: MaterialFields) -> Material:
    material = _own_material(db, material_id, user)
    values = data.model_dump(exclude_unset=True, mode="json")
    _check_material_files(user, values, material)
    old_file, old_cover = (material.file or {}).get("url"), material.cover_url
    for field, value in values.items():
        setattr(material, field, value)
    _check_material(material.kind, material.url, material.file)
    if "file" in values and old_file != (material.file or {}).get("url"):
        delete_own_url_after_commit(db, user.username, old_file)
    if "cover_url" in values and old_cover != material.cover_url:
        delete_own_url_after_commit(db, user.username, old_cover)
    db.commit()
    return material


def delete_material(db: Session, user, material_id: uuid.UUID) -> None:
    material = _own_material(db, material_id, user)
    delete_own_url_after_commit(db, user.username, (material.file or {}).get("url"))
    delete_own_url_after_commit(db, user.username, material.cover_url)
    db.delete(material)
    db.commit()


# ---------------------------------------------------------------- for other modules

def resolve_post_target(db: Session, post_id: uuid.UUID, user) -> Optional[Target]:
    """Comments on a post (registered with the discussion module)"""
    post = db.get(Post, post_id)
    if not post or post.author.is_hidden or (post.status == "draft" and (not user or user.id != post.author_id)):
        return None
    return Target(owner_id=post.author_id, has_recording=post.opus_id is not None)


def _count(db: Session, user_ids: list[uuid.UUID], *where) -> dict[uuid.UUID, int]:
    return dict(db.execute(
        select(Post.author_id, func.count()).where(Post.author_id.in_(user_ids), Post.status == "published", *where)
        .group_by(Post.author_id)
    ).all())


def count_posts(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Blog posts (what the «Блог» tab shows)"""
    return _count(db, user_ids, Post.kind == "note")


def count_articles(db: Session, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    return _count(db, user_ids, Post.kind == "article")


def recent_posts(db: Session, kinds: list[str], before, limit: int, seeking_feedback: bool = False) -> list[Post]:
    """New posts of the given kinds by visible members, newest first (the feed); or only the sketches
    whose authors ask for feedback"""
    stmt = select(Post).where(Post.status == "published", Post.kind.in_(kinds), visible_authors(Post.author_id))
    if seeking_feedback:
        stmt = stmt.where(Post.seeking_feedback.is_(True))
    if before:
        stmt = stmt.where(Post.created_at < before)
    return list(db.scalars(stmt.order_by(Post.created_at.desc()).limit(limit)).unique())


def search_posts(db: Session, words: list[str], limit: int) -> list[Post]:
    return list(db.scalars(
        select(Post).where(
            Post.status == "published", visible_authors(Post.author_id),
            textsearch.matches_all([Post.title, Post.excerpt, Post.content_md], words),
        ).order_by(Post.created_at.desc()).limit(limit)
    ).unique())
