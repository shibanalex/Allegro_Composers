"""HTTP layer of the chat module: the history, sending, deleting, and the pass to the live channel"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from allegro.core.db import get_db
from allegro.modules.accounts.deps import get_current_user, get_optional_user, require
from allegro.modules.accounts.roles import Capability
from allegro.modules.chat import service
from allegro.modules.chat.schemas import ConnectionOut, MessageIn, MessageOut, MessagePage

router = APIRouter(tags=["chat"])


@router.get("/api/chat/messages", response_model=MessagePage)
def history(before: Optional[uuid.UUID] = None, limit: int = Query(50, le=100), db: Session = Depends(get_db)):
    """Anyone may read the chat; the newest page, or the one before a message"""
    return service.history(db, before, limit)


@router.post("/api/chat/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send(data: MessageIn, user=Depends(require(Capability.CHAT)), db: Session = Depends(get_db)):
    return service.post(db, user, data.text)


@router.delete("/api/chat/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove(message_id: uuid.UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    service.delete(db, user, message_id)


@router.get("/api/chat/connection", response_model=ConnectionOut)
def connection(user=Depends(get_optional_user)):
    """A token for the WebSocket: a member's, or an anonymous listener's"""
    return service.connection(user)
