"""HTTP layer of the notifications module: the bell, the list, settings, push subscriptions"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from allegro.core.db import get_db
from allegro.modules.accounts.deps import get_current_user
from allegro.modules.notifications import service
from allegro.modules.notifications.schemas import (
    NotificationPage, PushSubscriptionIn, PushUnsubscribeIn, ReadIn, SettingsIn, SettingsOut, Unread,
)

router = APIRouter(tags=["notifications"])


@router.get("/api/notifications", response_model=NotificationPage)
def notifications(before: Optional[int] = None, limit: int = Query(30, ge=1, le=100),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    """What's new for me, newest first (only the kinds I chose)"""
    return service.list_notifications(db, user, before, limit)


@router.get("/api/notifications/unread", response_model=Unread)
def unread(user=Depends(get_current_user), db: Session = Depends(get_db)):
    """The number on the bell"""
    return Unread(count=service.unread_count(db, user))


@router.post("/api/notifications/read", response_model=Unread)
def read(data: ReadIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark some (ids) or all as read; answers how many are left unread"""
    return Unread(count=service.mark_read(db, user, data.ids))


@router.get("/api/notifications/settings", response_model=SettingsOut)
def get_settings(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.get_settings(db, user)


@router.put("/api/notifications/settings", response_model=SettingsOut)
def put_settings(data: SettingsIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return service.update_settings(db, user, data)


@router.post("/api/notifications/push", status_code=status.HTTP_204_NO_CONTENT)
def subscribe(data: PushSubscriptionIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    """This browser agrees to receive push notifications"""
    service.subscribe(db, user, data.endpoint, data.keys.p256dh, data.keys.auth)


@router.post("/api/notifications/push/remove", status_code=status.HTTP_204_NO_CONTENT)
def unsubscribe(data: PushUnsubscribeIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service.unsubscribe(db, user, data.endpoint)
