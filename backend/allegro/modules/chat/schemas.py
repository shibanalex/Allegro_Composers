"""What the chat API takes and gives"""
import re
import uuid
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from allegro.core.schemas import ORMModel, UTCDateTime
from allegro.modules.accounts.schemas import UserBrief

MAX_LENGTH = 2000


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_LENGTH)

    @field_validator("text")
    @classmethod
    def _text(cls, v: str) -> str:
        # control characters out (line breaks stay), no more than two empty lines in a row; an emoji alone is a message
        v = "".join(ch for ch in v.replace("\r", "") if ch in "\n\t" or ch.isprintable())
        v = "\n".join(line.rstrip() for line in v.split("\n"))
        v = re.sub(r"\n{4,}", "\n\n\n", v).strip()
        if not v:
            raise ValueError("Пустое сообщение")
        return v


class MessageOut(ORMModel):
    id: uuid.UUID
    text: str
    author: UserBrief
    created_at: UTCDateTime


class MessagePage(BaseModel):
    items: list[MessageOut]  # oldest first, as a chat reads
    next_before: Optional[str] = None  # the id to ask for older ones with; none; this is the beginning


class ConnectionOut(BaseModel):
    """How a browser joins the live chat"""
    url: str  # the WebSocket address, relative to the site
    token: str
    channel: str
