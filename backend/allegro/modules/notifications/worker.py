"""The worker: takes events from the outbox (core.events) in order and hands them to the notifications.

It runs as a background task inside the API process (started in allegro.main), so the site needs no
separate service. A failed event is retried up to MAX_ATTEMPTS times, then set aside with its error.
While the free hosting sleeps nothing is lost: the events wait in the database for the next wake-up.
"""
import asyncio
import logging
import time
from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from allegro.core.db import SessionLocal
from allegro.core.events import OutboxEvent, utcnow
from allegro.modules.notifications import service

log = logging.getLogger("allegro.worker")

POLL_SECONDS = 3
BATCH = 50
MAX_ATTEMPTS = 5
DIGEST_EVERY = 600  # seconds between checks whether someone's digest is due
KEEP_DONE = timedelta(days=7)


def process_pending(db: Session, limit: int = BATCH) -> int:
    """Handle the oldest pending events; returns how many were done"""
    events = list(db.scalars(
        select(OutboxEvent).where(OutboxEvent.processed_at.is_(None)).order_by(OutboxEvent.id).limit(limit)
    ))
    for event in events:
        try:
            service.handle(db, event.kind, event.payload or {})
            event.processed_at = utcnow()
            event.last_error = None
        except Exception as e:
            db.rollback()
            event = db.get(OutboxEvent, event.id)
            event.attempts += 1
            event.last_error = f"{type(e).__name__}: {e}"[:2000]
            if event.attempts >= MAX_ATTEMPTS:
                event.processed_at = utcnow()  # set aside; the error stays for a look
            log.warning("event %s (%s) failed, attempt %s: %s", event.id, event.kind, event.attempts, e)
        db.commit()
    return len(events)


def _tick(state: dict) -> None:
    with SessionLocal() as db:
        while process_pending(db) == BATCH:
            pass
        if time.monotonic() - state.get("digest", 0) > DIGEST_EVERY:
            state["digest"] = time.monotonic()
            service.send_digests(db)
            db.execute(delete(OutboxEvent).where(OutboxEvent.processed_at < utcnow() - KEEP_DONE))
            db.commit()


async def run() -> None:
    state: dict = {}
    while True:
        try:
            await run_in_threadpool(_tick, state)
        except Exception:  # the worker must outlive any single failure
            log.exception("notifications worker")
        await asyncio.sleep(POLL_SECONDS)
