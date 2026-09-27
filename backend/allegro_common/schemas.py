"""Pydantic building blocks shared by services"""
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, PlainSerializer


def _iso_utc(value: datetime) -> str:
    # SQLite drops tzinfo; all stored times are UTC
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UTCDateTime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserBrief(ORMModel):
    id: uuid.UUID
    username: str
    display_name: str
    pseudonym: Optional[str] = None
    avatar_url: Optional[str] = None


class Attachment(BaseModel):
    url: str
    name: str
    content_type: str = "application/octet-stream"
    size: Optional[int] = None
