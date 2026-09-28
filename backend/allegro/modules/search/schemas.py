"""Public data shapes of the search module"""
from typing import Optional

from pydantic import BaseModel

from allegro.core.schemas import UTCDateTime
from allegro.modules.accounts.schemas import UserBrief


class SearchComposer(UserBrief):
    bio: Optional[str] = None


class SearchOpus(BaseModel):
    slug: str
    title: str
    subtitle: Optional[str] = None
    author: UserBrief
    snippet: Optional[str] = None  # the words found in the description


class SearchPost(BaseModel):
    slug: str
    title: str
    kind: str
    author: UserBrief
    created_at: UTCDateTime
    snippet: str = ""  # the words found in the text (blog posts are often untitled)


class SearchResult(BaseModel):
    composers: list[SearchComposer]  # members of any role (the name is kept for older clients)
    opuses: list[SearchOpus]
    posts: list[SearchPost]
    tags: list[str]
    words: list[str] = []  # the stems searched for, to highlight them
