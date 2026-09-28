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
    content_md: str = Field(min_length=1, max_length=5000)

    @model_validator(mode="after")
    def _single_target(self):
        if (self.opus_id is None) == (self.post_id is None):
            raise ValueError("Укажите либо opus_id, либо post_id")
        return self


class CommentOut(ORMModel):
    id: uuid.UUID
    opus_id: Optional[uuid.UUID] = None
    post_id: Optional[uuid.UUID] = None
    parent_id: Optional[uuid.UUID] = None
    timestamp_marker: Optional[float] = None
    content_md: str
    created_at: UTCDateTime
    author: UserBrief
