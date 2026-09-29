"""Shared test setup: an isolated database and media folder, the application, and helpers"""
import http.cookiejar
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
# Every test request comes from one address: the flood limits are tested on their own (test_flood_protection)
os.environ["WRITE_REQUESTS_PER_MINUTE"] = "100000"
os.environ["SEARCH_REQUESTS_PER_MINUTE"] = "100000"

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from allegro.main import app

# The schema comes from the real migrations, so they are tested too
command.upgrade(Config("alembic.ini"), "head")

client = TestClient(app)
# Every test says who it is with an explicit header; a cookie jar would make «anonymous» requests signed in
client.cookies.jar.set_policy(http.cookiejar.DefaultCookiePolicy(allowed_domains=[]))


def token_of(response) -> str:
    """The login token the API put into its HttpOnly cookie"""
    return response.cookies["allegro_token"]

PDF = b"%PDF-1.4 fake score"


def register(username, display_name=None, role="composer", **extra):
    r = client.post("/api/auth/register", json={
        "username": username, "email": f"{username}@example.com", "password": "secret-pass",
        "display_name": display_name or username.title(), "role": role, **extra,
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {token_of(r)}"}


def picture(width=1200, height=600, fmt="PNG") -> bytes:
    """A real picture (uploads of pictures are decoded, so a few magic bytes are not enough)"""
    import io

    from PIL import Image
    out = io.BytesIO()
    Image.new("RGB", (width, height), (120, 80, 40)).save(out, fmt)
    return out.getvalue()


def upload(headers, name, content, content_type, purpose):
    r = client.post("/api/media", headers=headers, data={"purpose": purpose}, files={"files": (name, content, content_type)})
    assert r.status_code == 201, r.text
    return r.json()[0]


def create_opus(headers, **fields):
    body = {"title": "Трио ре минор", "genre": "trio", **fields}
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
    return {"Authorization": f"Bearer {token_of(r)}"}
