"""Migrations keep the data: a database at an older revision, full of content, upgraded to the newest one.

The database is opened the way the application opens it — with foreign keys enforced — because that is
exactly how rebuilding a table on SQLite once cascaded into deleting every work and post.
Run against PostgreSQL too:  MIGRATION_TEST_URL=postgresql://... python -m pytest tests/test_migrations.py
"""
import os
import tempfile
import uuid
from datetime import datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, event, text

import tests.support  # noqa: F401  (settings for the application's own imports)


def _engine():
    url = os.environ.get("MIGRATION_TEST_URL") or f"sqlite:///{tempfile.mkdtemp()}/migrations.db"
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_connection, _):
            dbapi_connection.execute("PRAGMA foreign_keys=ON")
    elif "MIGRATION_TEST_URL" in os.environ:
        with engine.begin() as c:  # a clean schema for the test
            c.exec_driver_sql("DROP SCHEMA public CASCADE; CREATE SCHEMA public")
    return engine


def _alembic(connection, revision: str) -> None:
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    config.attributes["configure_logger"] = False
    command.upgrade(config, revision)


@pytest.fixture()
def engine():
    engine = _engine()
    yield engine
    engine.dispose()


def test_upgrade_from_0005_keeps_every_work_and_post(engine):
    now = datetime.now(timezone.utc)
    owner, guest = uuid.uuid4(), uuid.uuid4()
    opus, post = uuid.uuid4(), uuid.uuid4()
    with engine.connect() as c:
        _alembic(c, "0005")
        uid = (lambda u: u.hex) if engine.dialect.name == "sqlite" else (lambda u: u)
        c.execute(text(
            "INSERT INTO users (id, username, email, password_hash, display_name, links, is_hidden, created_at) "
            "VALUES (:id, :u, :e, 'x', :n, '[]', :h, :t)"
        ), [
            {"id": uid(owner), "u": "owner", "e": "Owner@Example.com", "n": "Владелец", "h": False, "t": now},
            {"id": uid(guest), "u": "guest", "e": "guest@example.com", "n": "Гость", "h": False, "t": now.replace(year=now.year + 1)},
        ])
        c.execute(text(
            "INSERT INTO opuses (id, author_id, title, slug, ensemble, form, tags, audio_type, score_access, "
            "audio_offset_seconds, auto_page_markers, status, play_count, created_at, updated_at) "
            "VALUES (:id, :a, 'Трио', 'trio', 'chamber', 'sonata', '[]', 'none', 'free', 0, :f, 'published', 0, :t, :t)"
        ), {"id": uid(opus), "a": uid(owner), "t": now, "f": False})
        c.execute(text(
            "INSERT INTO posts (id, author_id, kind, title, slug, content_md, attachments, tags, status, view_count, created_at, updated_at) "
            "VALUES (:id, :a, 'note', '', 'zapis', 'Привет', '[]', '[]', 'published', 0, :t, :t)"
        ), {"id": uid(post), "a": uid(owner), "t": now})
        c.execute(text(
            "INSERT INTO comments (id, author_id, post_id, content_md, created_at) VALUES (:id, :a, :p, 'Браво', :t)"
        ), {"id": uid(uuid.uuid4()), "a": uid(guest), "p": uid(post), "t": now})
        c.commit()

        _alembic(c, "head")

        counts = {t: c.execute(text(f"SELECT count(*) FROM {t}")).scalar() for t in ("users", "opuses", "posts", "comments")}
        assert counts == {"users": 2, "opuses": 1, "posts": 1, "comments": 1}
        rows = {r.username: r for r in c.execute(text("SELECT username, role, is_admin, email_hash, email_encrypted FROM users"))}
        assert rows["owner"].is_admin and not rows["guest"].is_admin  # the earliest member is the owner
        assert rows["owner"].role == "composer"
        assert "example.com" not in rows["owner"].email_encrypted.lower()

    from allegro.core.security import decrypt_email, email_index
    assert decrypt_email(rows["owner"].email_encrypted) == "owner@example.com"
    assert rows["owner"].email_hash == email_index("owner@example.com")
