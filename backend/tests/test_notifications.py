"""Notifications: the outbox, the fan-out to members, the bell, push subscriptions, e-mail digests"""
from datetime import datetime, timedelta, timezone

import pytest

from tests.support import client, register, set_user

MEMBERS = ["n_author", "n_reader", "n_quiet"]


@pytest.fixture(scope="module", autouse=True)
def _leave_no_trace():
    yield
    for username in MEMBERS:
        set_user(username, is_hidden=True)


@pytest.fixture(scope="module")
def author():
    return register("n_author", "Автор", role="composer")


@pytest.fixture(scope="module")
def reader():
    return register("n_reader", "Читатель", role="listener")


def work():
    """What the worker would do in the background: handle the pending events"""
    from allegro.core.db import SessionLocal
    from allegro.modules.notifications.worker import process_pending
    with SessionLocal() as db:
        while process_pending(db):
            pass


def unread(headers):
    return client.get("/api/notifications/unread", headers=headers).json()["count"]


def test_a_new_post_reaches_every_member_but_its_author(author, reader):
    work()  # whatever other tests left
    client.post("/api/notifications/read", headers=reader, json={})
    before = unread(reader)
    post = client.post("/api/posts", headers=author, json={"kind": "note", "content_md": "Сегодня закончил сонату"}).json()
    assert unread(reader) == before  # nothing until the worker has run
    work()
    assert unread(reader) == before + 1
    page = client.get("/api/notifications", headers=reader).json()
    first = page["items"][0]
    assert first["actor"]["username"] == "n_author" and first["kind"] == "note" and first["url"] == f"/posts/{post['slug']}"
    assert first["title"].startswith("Сегодня закончил")
    assert all(n["actor"]["username"] != "n_author" for n in client.get("/api/notifications", headers=author).json()["items"])

    # read: the bell is empty again
    assert client.post("/api/notifications/read", headers=reader, json={"ids": [first["id"]]}).json()["count"] == before
    # a retried event doesn't notify twice
    from allegro.core.db import SessionLocal
    from allegro.modules.notifications import service
    with SessionLocal() as db:
        service.handle(db, "published", {"target_type": "post", "kind": "note", "id": post["id"], "author_id": first["actor"]["id"],
                                          "title": "x", "url": "/"})
    assert len([n for n in client.get("/api/notifications", headers=reader).json()["items"] if n["url"] == first["url"]]) == 1

    # the post is deleted: so is the notification
    client.delete(f"/api/posts/{post['slug']}", headers=author)
    work()
    assert all(n["url"] != first["url"] for n in client.get("/api/notifications", headers=reader).json()["items"])


def test_drafts_notify_only_when_published(author, reader):
    work()
    client.post("/api/notifications/read", headers=reader, json={})
    draft = client.post("/api/posts", headers=author, json={"kind": "article", "title": "Черновик", "content_md": "…", "status": "draft"}).json()
    work()
    assert unread(reader) == 0
    client.patch(f"/api/posts/{draft['slug']}", headers=author, json={"status": "published"})
    work()
    assert unread(reader) == 1


def test_members_choose_what_they_hear_about(author, reader):
    work()
    client.post("/api/notifications/read", headers=reader, json={})
    r = client.put("/api/notifications/settings", headers=reader, json={"kinds": ["opus", "sketch"]})
    assert r.status_code == 200 and r.json()["kinds"] == ["opus", "sketch"]
    client.post("/api/posts", headers=author, json={"kind": "note", "content_md": "Запись, которую читатель не ждёт"})
    work()
    assert unread(reader) == 0  # blog posts are off for this reader
    assert client.put("/api/notifications/settings", headers=reader, json={"kinds": []}).status_code == 422
    client.put("/api/notifications/settings", headers=reader, json={"kinds": ["opus", "sketch", "article", "performance", "note", "news"]})
    assert unread(reader) == 1  # back on: it was there all along


def test_the_shadowed_neither_notify_nor_are_notified(reader):
    quiet = register("n_quiet", "Тихий", role="composer")
    work()
    client.post("/api/notifications/read", headers=reader, json={})
    set_user("n_quiet", is_hidden=True)
    client.post("/api/posts", headers=quiet, json={"kind": "note", "content_md": "Из тени"})
    work()
    assert unread(reader) == 0


def test_push_subscriptions_and_delivery(author, reader, monkeypatch):
    from allegro.modules.notifications import push

    key = client.get("/api/notifications/settings", headers=reader).json()["push_key"]
    assert len(key) == 87  # a P-256 public key, uncompressed, base64url

    # only the browsers' own push services (the server sends requests there)
    evil = {"endpoint": "https://169.254.169.254/latest", "keys": {"p256dh": "x", "auth": "y"}}
    assert client.post("/api/notifications/push", headers=reader, json=evil).status_code == 422
    good = {"endpoint": "https://fcm.googleapis.com/fcm/send/abc", "keys": {"p256dh": "BPk", "auth": "au"}}
    assert client.post("/api/notifications/push", headers=reader, json=good).status_code == 204

    sent = []

    def fake_send(endpoint, p256dh, auth, message):
        sent.append((endpoint, message))
        raise push.Gone("410")  # the browser dropped it

    monkeypatch.setattr(push, "send", fake_send)
    work()
    client.post("/api/opuses", headers=author, json={"title": "Токката", "genre": "solo"})
    work()
    assert sent and sent[-1][0] == good["endpoint"] and "Токката" in sent[-1][1]["body"] and sent[-1][1]["url"].startswith("/opus/")
    sent.clear()
    client.post("/api/opuses", headers=author, json={"title": "Токката II", "genre": "solo"})
    work()
    assert not sent  # the dead subscription was forgotten


def test_email_digests(author, reader, monkeypatch):
    from allegro.core.config import settings
    from allegro.core.db import SessionLocal
    from allegro.modules.notifications import service

    assert client.put("/api/notifications/settings", headers=reader, json={"email": "daily"}).status_code == 422  # no mail set up
    for name, value in (("smtp_host", "smtp.example"), ("smtp_user", "site@example"), ("smtp_password", "x")):
        monkeypatch.setattr(settings, name, value)
    letters = []
    monkeypatch.setattr(service, "send_mail", lambda to, subject, text, html=None: letters.append((to, subject, text)))
    assert client.put("/api/notifications/settings", headers=reader, json={"email": "daily"}).json()["email"] == "daily"

    client.post("/api/posts", headers=author, json={"kind": "article", "title": "О канонах", "content_md": "…"})
    work()
    # the next 10:00 in Moscow (07:00 UTC): within a day of the post, whatever time the tests run at
    now = datetime.now(timezone.utc)
    morning = now.replace(hour=7, minute=0, second=0, microsecond=0)
    if morning <= now:
        morning += timedelta(days=1)
    with SessionLocal() as db:
        service.send_digests(db, now=morning)
        service.send_digests(db, now=morning + timedelta(hours=1))  # the same day: nothing more
    assert len(letters) == 1
    to, subject, text = letters[0]
    assert to == "n_reader@example.com" and "Allegro" in subject and "О канонах" in text and "/notifications" in text


def test_a_performance_links_to_the_work(author, reader):
    performer = register("n_violin", "Скрипачка", role="performer")
    MEMBERS.append("n_violin")
    opus = client.post("/api/opuses", headers=author, json={"title": "Каприс", "genre": "solo"}).json()
    work()
    r = client.post("/api/performances", headers=performer, json={
        "opus_id": opus["id"], "audio_type": "youtube", "audio_source": "https://youtu.be/dQw4w9WgXcQ",
    })
    assert r.status_code == 201, r.text
    work()
    first = client.get("/api/notifications", headers=reader).json()["items"][0]
    assert first["kind"] == "performance" and first["url"] == f"/opus/{opus['slug']}" and first["title"] == "Каприс"
