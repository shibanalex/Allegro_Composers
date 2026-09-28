"""Public data shapes of the site module"""
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, Field

from allegro.core.schemas import ORMModel, UTCDateTime
from allegro.modules.accounts.schemas import UserBrief

PageSlug = Literal["about", "links"]
FeedbackKind = Literal["idea", "bug", "other"]
FeedbackStatus = Literal["new", "planned", "done", "declined"]

FEEDBACK_KINDS = {"idea": "Идея", "bug": "Ошибка", "other": "Другое"}
FEEDBACK_STATUSES = {"new": "Новое", "planned": "В планах", "done": "Сделано", "declined": "Отклонено"}


class PageOut(BaseModel):
    slug: str
    content_md: str
    updated_at: Optional[UTCDateTime] = None


class PageIn(BaseModel):
    content_md: str = Field(max_length=50_000)


class FeedbackIn(BaseModel):
    kind: FeedbackKind = "idea"
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=1, max_length=5000)


class FeedbackUpdate(BaseModel):
    status: Optional[FeedbackStatus] = None
    reply_md: Optional[str] = Field(None, max_length=5000)


class FeedbackOut(ORMModel):
    id: uuid.UUID
    kind: str
    title: str
    body: str
    status: str
    reply_md: Optional[str] = None
    replied_at: Optional[UTCDateTime] = None
    created_at: UTCDateTime
    author: UserBrief


class FeedbackPage(BaseModel):
    items: list[FeedbackOut]
    total: int
