"""Public data shapes of the media module"""
from pydantic import BaseModel


class Uploaded(BaseModel):
    key: str
    url: str
    name: str
    content_type: str
    size: int
