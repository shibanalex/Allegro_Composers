"""The main page's feed: what appears in the members' halls, newest first.

A read-only composition of the other modules — this module stores nothing. Every source returns at most
`limit` entries older than the cursor, the entries are merged by time and cut to `limit`: a page costs
a few indexed queries whatever the size of the site. (Later: a recommendation order instead of time.)
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from allegro.modules.catalog.service import opuses_out, performance_out, recent_opuses, recent_performances
from allegro.modules.discussion.schemas import ReactionsOut
from allegro.modules.discussion.service import reaction_summary
from allegro.modules.feed.schemas import FeedItem, FeedPage
from allegro.modules.publications.service import posts_out, recent_posts

# What each tab of the feed shows
SOURCES = {
    "all": ("opuses", "performances", "articles", "blogs", "news"),
    "works": ("opuses",),
    "performances": ("performances",),
    "articles": ("articles",),
    "blogs": ("blogs",),
}
POST_SOURCES = (("article", "articles"), ("note", "blogs"), ("news", "news"))


def _aware(value: datetime) -> datetime:
    """SQLite gives back naive datetimes; every stored time is UTC"""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _with_likes(db: Session, items: list[FeedItem], user) -> None:
    """Likes of the whole page: one query per type of entry, not one per entry"""
    for type_ in ("opus", "performance", "post"):
        page = {getattr(item, type_).id: item for item in items if item.type == type_}
        for target_id, r in reaction_summary(db, type_, list(page), user).items():
            page[target_id].likes = ReactionsOut(count=r.count, mine=r.mine)


def feed(db: Session, kind: str, before: Optional[datetime], limit: int, user=None) -> FeedPage:
    sources = SOURCES[kind]
    items: list[FeedItem] = []
    if "opuses" in sources:
        items += [FeedItem(type="opus", created_at=o.created_at, opus=o)
                  for o in opuses_out(db, recent_opuses(db, before, limit))]
    if "performances" in sources:
        items += [FeedItem(type="performance", created_at=p.created_at, performance=performance_out(p))
                  for p in recent_performances(db, before, limit)]
    post_kinds = [kind_ for kind_, source in POST_SOURCES if source in sources]
    if post_kinds:
        items += [FeedItem(type="post", created_at=p.created_at, post=p)
                  for p in posts_out(db, recent_posts(db, post_kinds, before, limit))]
    items.sort(key=lambda item: _aware(item.created_at), reverse=True)
    page = items[:limit]
    _with_likes(db, page, user)
    # a full page may have more behind it; a short one is the end
    next_before = _aware(page[-1].created_at).isoformat() if len(page) == limit else None
    return FeedPage(items=page, next_before=next_before)
