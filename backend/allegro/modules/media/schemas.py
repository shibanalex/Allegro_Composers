"""Public data shapes of the media module"""
from typing import Optional

from pydantic import BaseModel


class Uploaded(BaseModel):
    key: str
    url: str
    name: str
    content_type: str
    size: int
    preview_url: Optional[str] = None  # pictures: a light copy for cards and lists
