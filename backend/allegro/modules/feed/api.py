"""HTTP layer of the feed module"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from allegro.core.db import get_db
from allegro.modules.accounts.deps import get_optional_user
from allegro.modules.feed import service
from allegro.modules.feed.schemas import FeedKind, FeedPage

router = APIRouter(tags=["feed"])


@router.get("/api/feed", response_model=FeedPage)
def feed(
    kind: FeedKind = "all",
    before: Optional[datetime] = None,
    limit: int = Query(15, ge=1, le=50),
    user=Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """The main page: new works, performances, articles and blog posts from every hall, newest first"""
    return service.feed(db, kind, before, limit, user)
