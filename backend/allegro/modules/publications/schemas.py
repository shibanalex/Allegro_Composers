"""Public data shapes of the publications module"""
import re
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from allegro.core.schemas import Attachment, ORMModel, UTCDateTime
from allegro.modules.accounts.schemas import UserBrief
from allegro.modules.catalog.schemas import OpusBrief
from allegro.modules.discussion.schemas import ReactionsOut

# note: a blog post (everyone) · sketch: a quick recording with a short title (composers) · article: an article
# or review (composers, theorists) · news: the site's news (administrators) · workshop: an old review request
Kind = Literal["article", "note", "sketch", "news", "workshop"]
Status = Literal["published", "draft", "unlisted"]

POST_KINDS = {
    "note": "Запись в блоге",
    "sketch": "Эскиз",
    "article": "Статья",
    "news": "Новости",
    "workshop": "Мастерская",
}

MATERIAL_KINDS = {
    "book": "Книги",
    "link": "Ссылки",
    "file": "Файлы",
}


class PostFields(BaseModel):
    kind: Optional[Kind] = None
    title: Optional[str] = Field(None, max_length=255)  # may be empty for a blog post, like a channel message
    excerpt: Optional[str] = Field(None, max_length=512)
    content_md: Optional[str] = Field(None, max_length=100_000)
    cover_url: Optional[str] = Field(None, max_length=512)
    attachments: Optional[list[Attachment]] = Field(None, max_length=50)
    tags: Optional[list[str]] = None
    opus_id: Optional[uuid.UUID] = None  # a post about a specific opus
    quote_post_id: Optional[uuid.UUID] = None  # a post quoting another one (a repost with one's own words)
    seeking_feedback: Optional[bool] = None  # sketches: «ищу отзыв»
    status: Optional[Status] = None


class PostCreate(PostFields):
    kind: Kind
    title: str = Field("", max_length=255)
    content_md: str = ""


class PostBrief(ORMModel):
    """A post as another post shows it: a quotation, a mention"""
    id: uuid.UUID
    slug: str
    kind: str
    title: str
    preview: str = ""  # the beginning of the text
    image_url: Optional[str] = None  # the cover or the first picture
    created_at: UTCDateTime
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
    quote: Optional[PostBrief] = None
    seeking_feedback: bool = False
    comment_count: int = 0
    likes: Optional[ReactionsOut] = None  # on the post's own page: with it, so the page needs one request


class PostPage(BaseModel):
    items: list[PostOut]
    total: int


# ---------------------------------------------------------------- materials

MaterialKind = Literal["book", "link", "file"]


class MaterialFields(BaseModel):
    kind: Optional[MaterialKind] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=4000)
    url: Optional[str] = Field(None, max_length=1024)
    file: Optional[Attachment] = None
    cover_url: Optional[str] = Field(None, max_length=512)
    position: Optional[int] = None

    @field_validator("url")
    @classmethod
    def _http_only(cls, v):
        if v and not re.match(r"^https?://", v.strip()):
            raise ValueError("Ссылка должна начинаться с http:// или https://")
        return v.strip() if v else v


class MaterialIn(MaterialFields):
    kind: MaterialKind
    title: str = Field(min_length=1, max_length=255)


class MaterialOut(ORMModel):
    id: uuid.UUID
    kind: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    file: Optional[Attachment] = None
    cover_url: Optional[str] = None
    position: int
    created_at: UTCDateTime
