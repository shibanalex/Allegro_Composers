"""HTTP layer of the search module (Ctrl+K and the /search page)"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from allegro.core.db import get_db
from allegro.modules.search import service
from allegro.modules.search.schemas import SearchResult

router = APIRouter(tags=["search"])


@router.get("/api/search", response_model=SearchResult)
def search(q: str = Query(min_length=1, max_length=100), limit: int = Query(5, ge=1, le=50), db: Session = Depends(get_db)):
    """Members, works, posts (titles and texts) and tags; every word must be found, any ending"""
    return service.search(db, q, limit)
