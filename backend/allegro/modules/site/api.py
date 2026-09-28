"""HTTP layer of the site module: «О нас», «Ссылки», «Предложения»"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from allegro.core.db import get_db
from allegro.modules.accounts.deps import get_admin, get_current_user
from allegro.modules.site import service
from allegro.modules.site.schemas import (
    FeedbackIn, FeedbackOut, FeedbackPage, FeedbackStatus, FeedbackUpdate, PageIn, PageOut, PageSlug,
)

router = APIRouter(tags=["site"])


@router.get("/api/site/pages/{slug}", response_model=PageOut)
def get_page(slug: PageSlug, db: Session = Depends(get_db)):
    return service.get_page(db, slug)


@router.put("/api/site/pages/{slug}", response_model=PageOut)
def put_page(slug: PageSlug, data: PageIn, admin=Depends(get_admin), db: Session = Depends(get_db)):
    return service.put_page(db, admin, slug, data.content_md)


@router.get("/api/feedback", response_model=FeedbackPage)
def list_feedback(
    status_filter: Optional[FeedbackStatus] = Query(None, alias="status"),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Everyone sees the suggestions and their answers, so ideas aren't repeated"""
    items, total = service.list_feedback(db, status_filter, limit, offset)
    return FeedbackPage(items=items, total=total)


@router.post("/api/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def create_feedback(data: FeedbackIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.create_feedback(db, user, data)


@router.patch("/api/feedback/{feedback_id}", response_model=FeedbackOut)
def update_feedback(feedback_id: uuid.UUID, data: FeedbackUpdate, _=Depends(get_admin), db: Session = Depends(get_db)):
    return service.update_feedback(db, feedback_id, data)


@router.delete("/api/feedback/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(feedback_id: uuid.UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service.delete_feedback(db, user, feedback_id)
