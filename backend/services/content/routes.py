"""Content service: theory articles, personal notes (the author's blog) and workshop threads"""
import uuid
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from allegro_common.db import get_db
from allegro_common.deps import get_current_user, get_optional_user
from allegro_common.media_refs import check_url, delete_own
from allegro_common.models import Comment, Opus, Post, User
from allegro_common.schemas import Attachment, ORMModel, UserBrief, UTCDateTime
from allegro_common.storage import storage
from allegro_common.utils import unique_slug, visible_authors

router = APIRouter(tags=["content"])

Kind = Literal["article", "note", "workshop"]
Status = Literal["published", "draft", "unlisted"]


class PostFields(BaseModel):
    kind: Optional[Kind] = None
    title: Optional[str] = Field(None, max_length=255)  # may be empty for a blog post, like a channel message
    excerpt: Optional[str] = Field(None, max_length=512)
    content_md: Optional[str] = Field(None, max_length=100_000)
    cover_url: Optional[str] = Field(None, max_length=512)
    attachments: Optional[list[Attachment]] = Field(None, max_length=50)
    tags: Optional[list[str]] = None
    opus_id: Optional[uuid.UUID] = None  # workshop thread about a specific opus
    status: Optional[Status] = None


class PostCreate(PostFields):
    kind: Kind
    title: str = Field("", max_length=255)
    content_md: str = ""


class OpusBrief(ORMModel):
    id: uuid.UUID
    slug: str
    title: str
    subtitle: Optional[str] = None
    audio_type: str
    audio_source: Optional[str] = None
    audio_url: Optional[str] = None
    audio_duration_seconds: Optional[float] = None
    author: UserBrief


class PostOut(ORMModel):
    id: uuid.UUID
    slug: str
    kind: str
    title: str
    excerpt: Optional[str] = None
    content_md: str
    cover_url: Optional[str] = None
    attachments: list[Attachment] = []
    tags: list[str] = []
    status: str
    view_count: int
    created_at: UTCDateTime
    author: UserBrief
    opus: Optional[OpusBrief] = None
    comment_count: int = 0


class PostPage(BaseModel):
    items: list[PostOut]
    total: int


def _opus_brief(opus: Optional[Opus]) -> Optional[OpusBrief]:
    if not opus or opus.status == "draft" or opus.author.is_hidden:
        return None
    brief = OpusBrief.model_validate(opus)
    return brief.model_copy(update={"audio_url": storage.url(opus.audio_source) if opus.audio_type == "hosted_file" else None})


def _outs(db: Session, posts: list[Post]) -> list[PostOut]:
    ids = [p.id for p in posts]
    counts = dict(db.execute(
        select(Comment.post_id, func.count()).where(Comment.post_id.in_(ids)).group_by(Comment.post_id)
    ).all()) if ids else {}
    return [
        PostOut.model_validate(p).model_copy(update={"opus": _opus_brief(p.opus), "comment_count": counts.get(p.id, 0)})
        for p in posts
    ]


def _check_opus(db: Session, opus_id: Optional[uuid.UUID]) -> None:
    if opus_id:
        opus = db.get(Opus, opus_id)
        if not opus or opus.status == "draft":
            raise HTTPException(422, "Опус не найден")


def _get_post(db: Session, slug: str, user: Optional[User]) -> Post:
    post = db.scalar(select(Post).where(Post.slug == slug, visible_authors(Post.author_id)))
    if not post or (post.status == "draft" and (not user or user.id != post.author_id)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Публикация не найдена")
    return post


def _own_post(db: Session, slug: str, user: User) -> Post:
    post = _get_post(db, slug, user)
    if post.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Это не ваша публикация")
    return post


@router.get("/api/posts", response_model=PostPage)
def list_posts(
    kind: Optional[list[Kind]] = Query(None),
    author: Optional[str] = None,
    opus: Optional[str] = None,
    mine: bool = False,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    stmt = select(Post).join(Post.author)
    if mine:
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Требуется вход")
        stmt = stmt.where(Post.author_id == user.id)
    else:
        stmt = stmt.where(Post.status == "published", User.is_hidden.is_(False))
    if kind:
        stmt = stmt.where(Post.kind.in_(kind))
    if author:
        stmt = stmt.where(User.username == author.lower())
    if opus:
        stmt = stmt.where(Post.opus.has(Opus.slug == opus))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    posts = db.scalars(stmt.order_by(Post.created_at.desc()).offset(offset).limit(limit)).unique().all()
    return PostPage(items=_outs(db, list(posts)), total=total)


@router.get("/api/posts/{slug}", response_model=PostOut)
def get_post(slug: str, user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    post = _get_post(db, slug, user)
    db.execute(update(Post).where(Post.id == post.id).values(view_count=Post.view_count + 1))
    db.commit()
    db.refresh(post)
    return _outs(db, [post])[0]


def _check_text(kind: str, title: str, content: str, attachments: list) -> None:
    """Articles and workshop threads need a title; a blog post is like a channel message: text or media is enough"""
    if kind != "note" and not title.strip():
        raise HTTPException(422, "Нужен заголовок")
    if not content.strip() and not attachments:
        raise HTTPException(422, "Пустая запись")


def _check_files(user: User, values: dict, post: Optional[Post] = None) -> None:
    """Cover and attachments must be the author's own uploads (or already on this post)"""
    current = [post.cover_url, *(a.get("url") for a in post.attachments or [])] if post else []
    if "cover_url" in values:
        check_url(user, values["cover_url"], current)
    for attachment in values.get("attachments") or []:
        check_url(user, attachment["url"], current)


def _slug_source(title: str, content: str) -> str:
    return title.strip() or " ".join(content.split()[:6]) or "zapis"


@router.post("/api/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
def create_post(data: PostCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_text(data.kind, data.title, data.content_md, data.attachments or [])
    _check_opus(db, data.opus_id)
    values = data.model_dump(exclude_none=True, mode="json")
    _check_files(user, values)
    values["title"] = data.title.strip()
    if data.opus_id:
        values["opus_id"] = data.opus_id
    post = Post(author_id=user.id, slug=unique_slug(db, Post.slug, _slug_source(data.title, data.content_md)), **values)
    db.add(post)
    db.commit()
    return _outs(db, [post])[0]


@router.patch("/api/posts/{slug}", response_model=PostOut)
def update_post(slug: str, data: PostFields, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _own_post(db, slug, user)
    values = data.model_dump(exclude_unset=True, mode="json")
    _check_files(user, values, post)
    if "opus_id" in values:
        _check_opus(db, data.opus_id)
        values["opus_id"] = data.opus_id
    for field, value in values.items():
        setattr(post, field, value)
    _check_text(post.kind, post.title or "", post.content_md or "", post.attachments or [])
    db.commit()
    return _outs(db, [post])[0]


@router.delete("/api/posts/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = _own_post(db, slug, user)
    delete_own(user, storage.key_from_url(post.cover_url))
    for attachment in post.attachments or []:
        delete_own(user, storage.key_from_url(attachment.get("url")))
    db.delete(post)
    db.commit()
