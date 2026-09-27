"""Database engine and session management (shared by all services)"""
import json
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from allegro_common.config import settings

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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
