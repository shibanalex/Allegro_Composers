"""Public data shapes of the feed module"""
from typing import Literal, Optional

from pydantic import BaseModel

from allegro.core.schemas import UTCDateTime
from allegro.modules.catalog.schemas import OpusOut, PerformanceOut
from allegro.modules.discussion.schemas import CommentPreview, ReactionsOut
from allegro.modules.publications.schemas import PostOut

FeedKind = Literal["all", "works", "sketches", "feedback", "performances", "articles", "blogs"]


class FeedItem(BaseModel):
    """One entry of the feed: exactly one of opus / performance / post is set"""
    type: Literal["opus", "performance", "post"]
    created_at: UTCDateTime
    opus: Optional[OpusOut] = None
    performance: Optional[PerformanceOut] = None
    post: Optional[PostOut] = None
    likes: ReactionsOut = ReactionsOut(count=0, mine=False)
    comments: list[CommentPreview] = []  # the last ones (works and posts), from the cache


class FeedPage(BaseModel):
    items: list[FeedItem]
    next_before: Optional[str] = None  # pass as `before` for the next page; None; the end
