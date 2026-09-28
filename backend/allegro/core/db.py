"""Database engine, the declarative base and the request session.

Transactions: a use case (a module's service function) makes its changes and calls `db.commit()`
once at the end. Side effects that must only happen if the data really was saved — deleting a replaced
file from storage, for example — are registered with `after_commit(db, fn)`: they run right after a
successful commit and are dropped on rollback, so a failed save never loses a file the database still
points to.
"""
import json
import logging
from typing import Callable, Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from allegro.core.config import settings

log = logging.getLogger(__name__)

_is_sqlite = settings.database_url.startswith("sqlite")

engine = create_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    # SQLite: one file shared by threads. PostgreSQL behind a transaction-mode pooler (Neon "-pooler",
    # PgBouncer): a backend connection changes between transactions, so psycopg's server-side
    # prepared statements could vanish mid-session - they are switched off.
    connect_args={"check_same_thread": False} if _is_sqlite else {"prepare_threshold": None},
    # Keep Cyrillic readable inside JSON columns (tag search relies on it)
    json_serializer=lambda obj: json.dumps(obj, ensure_ascii=False),
)

if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _sqlite_setup(dbapi_connection, _):
        # SQLite's built-in lower() only folds ASCII; match PostgreSQL behaviour for Cyrillic search
        dbapi_connection.create_function("lower", 1, lambda s: s.lower() if isinstance(s, str) else s, deterministic=True)
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: one session per request. Anything not committed by the use case is rolled back."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------- side effects after commit

_HOOKS = "after_commit_hooks"


def after_commit(db: Session, fn: Callable[[], None]) -> None:
    """Run `fn` once the current transaction is committed; forget it if the transaction is rolled back"""
    db.info.setdefault(_HOOKS, []).append(fn)


@event.listens_for(Session, "after_commit")
def _run_hooks(session: Session) -> None:
    for fn in session.info.pop(_HOOKS, []):
        try:
            fn()
        except Exception:  # the data is saved; a failed cleanup is logged, never turned into an error
            log.exception("after-commit hook failed")


@event.listens_for(Session, "after_rollback")
def _drop_hooks(session: Session) -> None:
    session.info.pop(_HOOKS, None)
