"""Public data shapes of the discussion module"""
import uuid
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from allegro.core.schemas import ORMModel, UTCDateTime
from allegro.modules.accounts.schemas import UserBrief


class CommentIn(BaseModel):
    opus_id: Optional[uuid.UUID] = None
    post_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    timestamp_marker: Optional[float] = Field(None, ge=0)
    timestamp_end: Optional[float] = Field(None, ge=0)  # a stretch: from timestamp_marker to timestamp_end
    content_md: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def _single_target(self):
        if (self.opus_id is None) == (self.post_id is None):
            raise ValueError("Укажите либо opus_id, либо post_id")
        if self.timestamp_end is not None:
            if self.timestamp_marker is None:
                raise ValueError("У отрезка должно быть начало")
            if self.timestamp_end - self.timestamp_marker < 0.5:
                raise ValueError("Отрезок должен кончаться позже, чем начинается")
        return self


class CommentPreview(BaseModel):
    """One of the last comments under a feed entry"""
    id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    content_md: str
    created_at: UTCDateTime
    author: UserBrief


class ReactionsOut(BaseModel):
    count: int
    mine: bool  # the reader liked it


class CommentOut(ORMModel):
    id: uuid.UUID
    opus_id: Optional[uuid.UUID] = None
    post_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    timestamp_marker: Optional[float] = None
    timestamp_end: Optional[float] = None
    content_md: str
    created_at: UTCDateTime
    author: UserBrief
