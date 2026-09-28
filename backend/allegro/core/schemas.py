"""Pydantic building blocks shared by modules"""
from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer


def _iso_utc(value: datetime) -> str:
    # SQLite drops tzinfo; all stored times are UTC
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


UTCDateTime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str)]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Attachment(BaseModel):
    url: str = Field(max_length=512)
    name: str = Field(max_length=255)
    content_type: str = Field("application/octet-stream", max_length=127)
    size: Optional[int] = None
