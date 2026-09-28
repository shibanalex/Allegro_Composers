"""Shared test setup: an isolated database and media folder, the application, and helpers"""
import os
import tempfile

# Isolated database and media dir - must be set before allegro is imported
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["MEDIA_DIR"] = f"{_tmp}/media"
# Open community regardless of a local .env (the invitation tests switch it themselves)
os.environ["REGISTRATION_MODE"] = "open"
os.environ.pop("REGISTRATION_OPEN", None)
os.environ["SECRET_KEY"] = "test-secret-key-long-enough-for-hs256-signing"

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from allegro.main import app

# The schema comes from the real migrations, so they are tested too
command.upgrade(Config("alembic.ini"), "head")

client = TestClient(app)

PDF = b"%PDF-1.4 fake score"


def register(username, display_name=None, role="composer", **extra):
    r = client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@example.com", "password": "secret-pass",
        "display_name": display_name or username.title(), "role": role, **extra,
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def upload(headers, name, content, content_type, purpose):
    r = client.post("/api/media", headers=headers, data={"purpose": purpose}, files={"files": (name, content, content_type)})
    assert r.status_code == 201, r.text
    return r.json()[0]


def create_opus(headers, **fields):
    body = {"title": "Трио ре минор", "ensemble": "chamber", "form": "sonata", **fields}
    r = client.post("/api/opuses", headers=headers, json=body)
    assert r.status_code == 201, r.text
    return r.json()




def set_user(username, **values):
    """Change an account directly in the database (hide it, make it an administrator…)"""
    from allegro.core.db import SessionLocal
    from allegro.modules.accounts.models import User
    with SessionLocal() as db:
        db.query(User).filter(User.username == username).update(values)
        db.commit()


def login(username, password="secret-pass"):
    r = client.post("/api/auth/login", json={"login": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
