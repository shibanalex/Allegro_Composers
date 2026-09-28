"""Public data shapes of the feed module"""
from typing import Literal, Optional

from pydantic import BaseModel

from allegro.core.schemas import UTCDateTime
from allegro.modules.catalog.schemas import OpusOut, PerformanceOut
from allegro.modules.publications.schemas import PostOut

FeedKind = Literal["all", "works", "performances", "articles", "blogs"]


class FeedItem(BaseModel):
    """One entry of the feed: exactly one of opus / performance / post is set"""
    type: Literal["opus", "performance", "post"]
    created_at: UTCDateTime
    opus: Optional[OpusOut] = None
    performance: Optional[PerformanceOut] = None
    post: Optional[PostOut] = None


class FeedPage(BaseModel):
    items: list[FeedItem]
    next_before: Optional[str] = None  # pass as `before` for the next page; None — the end
