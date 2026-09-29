"""Public data shapes of the notifications module"""
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

from allegro.core.schemas import ORMModel, UTCDateTime
from allegro.modules.accounts.schemas import UserBrief

# What a notification can be about (the kinds of publications)
KINDS = ("opus", "sketch", "article", "performance", "note", "news")
Kind = Literal["opus", "sketch", "article", "performance", "note", "news"]
EmailMode = Literal["off", "daily", "weekly"]


class NotificationOut(ORMModel):
    id: int
    kind: str
    title: str
    url: str
    created_at: UTCDateTime
    read_at: Optional[UTCDateTime] = None
    actor: Optional[UserBrief] = None


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    unread: int
    next_before: Optional[int] = None  # the id to pass as `before` for older ones


class Unread(BaseModel):
    count: int


class ReadIn(BaseModel):
    ids: Optional[list[int]] = Field(None, max_length=200)  # none: everything


class SettingsOut(BaseModel):
    kinds: list[str]
    push: bool
    email: EmailMode
    email_available: bool  # the site can send mail and the member has an address
    push_key: str  # the site's public key for the browser's push subscription


class SettingsIn(BaseModel):
    kinds: Optional[list[Kind]] = None
    push: Optional[bool] = None
    email: Optional[EmailMode] = None

    @field_validator("kinds")
    @classmethod
    def _some(cls, v):
        return list(dict.fromkeys(v)) if v is not None else v


class PushKeys(BaseModel):
    p256dh: str = Field(max_length=255)
    auth: str = Field(max_length=255)


class PushSubscriptionIn(BaseModel):
    endpoint: str = Field(max_length=1024)
    keys: PushKeys


class PushUnsubscribeIn(BaseModel):
    endpoint: str = Field(max_length=1024)
