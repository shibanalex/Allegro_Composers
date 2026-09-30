"""Roles, invitations, administration, performances, the showcase, site pages and suggestions"""
import pytest

from tests.support import client, create_opus, login, register, set_user, token_of, upload


MEMBERS = ["mira", "ivan_theory", "vera_violin", "sam_listens", "new_one", "petr_cello"]


@pytest.fixture(scope="module", autouse=True)
def _leave_no_trace():
    """Other test files count works and posts on the same database: afterwards these members go in the shadow"""
    yield
    for username in MEMBERS:
        set_user(username, is_hidden=True)


@pytest.fixture(scope="module")
def admin():
    headers = register("mira", "Мира Основательница")
    set_user("mira", is_admin=True)
    return headers


@pytest.fixture(scope="module")
def theorist():
    return register("ivan_theory", "Иван Теоретик", role="theorist")


@pytest.fixture(scope="module")
def performer():
    return register("vera_violin", "Вера Скрипачка", role="performer")


@pytest.fixture(scope="module")
def listener():
    return register("sam_listens", "Сэм", role="listener")


# ---------------------------------------------------------------- roles

def test_roles_decide_what_can_be_published(admin, theorist, performer, listener):
    me = client.get("/api/auth/me", headers=listener).json()
    assert me["role"] == "listener" and me["capabilities"] == ["comment", "publish_note", "react", "share_material"]
    # everyone keeps a blog
    for who in (theorist, performer, listener):
        assert client.post("/api/posts", headers=who, json={"kind": "note", "content_md": "Привет"}).status_code == 201
    # articles: composers and theorists
    article = {"kind": "article", "title": "О полифонии", "content_md": "Текст"}
    assert client.post("/api/posts", headers=theorist, json=article).status_code == 201
    r = client.post("/api/posts", headers=performer, json=article)
    assert r.status_code == 403 and "теоретики" in r.json()["detail"]
    # works: composers only
    assert client.post("/api/opuses", headers=theorist, json={"title": "X", "genre": "solo"}).status_code == 403
    # news: administrators only
    news = {"kind": "news", "title": "Открытие", "content_md": "Мы открылись"}
    assert client.post("/api/posts", headers=theorist, json=news).status_code == 403
    assert client.post("/api/posts", headers=admin, json=news).status_code == 201
    assert client.get("/api/posts", params={"kind": "news"}).json()["total"] == 1


def test_role_and_hall_style_are_chosen_by_the_member(listener):
    r = client.patch("/api/users/me", headers=listener, json={"role": "performer", "hall_theme": "avantgarde"})
    assert r.status_code == 200 and r.json()["role"] == "performer" and "publish_performance" in r.json()["capabilities"]
    assert client.get("/api/users/sam_listens").json()["hall_theme"] == "avantgarde"
    assert client.patch("/api/users/me", headers=listener, json={"hall_theme": "rococo"}).status_code == 422
    client.patch("/api/users/me", headers=listener, json={"role": "listener"})


# ---------------------------------------------------------------- joining

def test_anyone_can_join(admin, monkeypatch):
    from allegro.core.ratelimit import AttemptLimiter
    from allegro.modules.accounts import service
    assert "registration" not in client.get("/api/auth/config").json()

    body = {"username": "new_one", "display_name": "Новичок", "password": "secret-pass", "role": "performer"}
    r = client.post("/api/auth/register", json=body)  # no invitation, and e-mail is optional
    assert r.status_code == 201, r.text
    assert r.json()["user"]["email"] is None and r.json()["user"]["role"] == "performer"
    set_user("new_one", is_hidden=True)
    # there are no invitations any more
    assert client.post("/api/admin/invites", headers=admin, json={}).status_code in (404, 405)
    assert client.get("/api/admin/links", headers=admin).status_code in (404, 405)

    # one address opens only a few accounts an hour: bots don't fill the site with members
    monkeypatch.setattr(service, "signup_limiter", AttemptLimiter(2, 3600, "Много залов."))
    codes = [client.post("/api/auth/register", json={**body, "username": f"bulk_{i}"}).status_code for i in range(3)]
    assert codes == [201, 201, 429]
    assert client.get("/api/users/bulk_2").status_code == 404
    for i in range(2):
        set_user(f"bulk_{i}", is_hidden=True)


def test_password_reset_link(admin, performer):
    users = client.get("/api/admin/users", headers=admin).json()
    vera = next(u for u in users if u["username"] == "vera_violin")
    assert vera["has_email"] is True and "email" not in vera
    link = client.post(f"/api/admin/users/{vera['id']}/reset-link", headers=admin).json()
    assert client.get(f"/api/auth/links/{link['token']}").json()["username"] == "vera_violin"
    r = client.post("/api/auth/reset", json={"token": link["token"], "password": "brand-new-pass"})
    assert r.status_code == 200
    assert client.post("/api/auth/login", json={"login": "vera_violin", "password": "secret-pass"}).status_code == 401
    login("vera_violin", "brand-new-pass")
    assert client.post("/api/auth/reset", json={"token": link["token"], "password": "another-pass"}).status_code == 403
    # a new link replaces the one made before it
    first = client.post(f"/api/admin/users/{vera['id']}/reset-link", headers=admin).json()
    second = client.post(f"/api/admin/users/{vera['id']}/reset-link", headers=admin).json()
    assert client.get(f"/api/auth/links/{first['token']}").json()["valid"] is False
    assert client.get(f"/api/auth/links/{second['token']}").json()["valid"] is True
    # the reset signed her out everywhere (the fixture's token too): back to the start for the next tests
    set_user("vera_violin", password_hash=_hash("secret-pass"), session_version=0)


def _hash(password):
    from allegro.core.security import hash_password
    return hash_password(password)


def test_email_is_stored_encrypted(theorist):
    from allegro.core.db import SessionLocal
    from allegro.modules.accounts.models import User
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == "ivan_theory").one()
        assert "ivan_theory@example.com" not in (user.email_encrypted or "")
        assert user.email_hash and len(user.email_hash) == 64
    assert client.get("/api/auth/me", headers=theorist).json()["email"] == "ivan_theory@example.com"
    login("IVAN_THEORY@example.com")  # sign in by e-mail still works
    # changing and removing
    assert client.patch("/api/users/me", headers=theorist, json={"email": "mira@example.com"}).status_code == 409  # taken
    assert client.patch("/api/users/me", headers=theorist, json={"email": ""}).json()["email"] is None


def test_admin_cannot_lock_themselves_out(admin):
    users = client.get("/api/admin/users", headers=admin).json()
    me = next(u for u in users if u["username"] == "mira")
    assert client.patch(f"/api/admin/users/{me['id']}", headers=admin, json={"is_admin": False}).status_code == 422
    assert client.patch(f"/api/admin/users/{me['id']}", headers=admin, json={"is_hidden": True}).status_code == 422


# ---------------------------------------------------------------- showcase and performances

def test_showcase_lists_featured_works(admin):
    create_opus(admin, title="Этюд", genre="solo", featured=True)
    create_opus(admin, title="Набросок", genre="solo")
    featured = client.get("/api/opuses", params={"author": "mira", "featured": True}).json()
    assert [o["title"] for o in featured["items"]] == ["Этюд"]
    assert client.get("/api/opuses", params={"author": "mira"}).json()["total"] == 2
    facets = client.get("/api/library/facets", params={"author": "mira"}).json()
    assert next(f for f in facets["genres"] if f["value"] == "solo")["count"] == 2


def test_performances(admin, performer, theorist):
    etude = client.get("/api/opuses", params={"author": "mira", "q": "Этюд"}).json()["items"][0]
    body = {"opus_id": etude["id"], "audio_type": "youtube", "audio_source": "https://youtu.be/dQw4w9WgXcQ"}
    assert client.post("/api/performances", headers=theorist, json=body).status_code == 403  # not a performer
    r = client.post("/api/performances", headers=performer, json=body)
    assert r.status_code == 201, r.text
    perf = r.json()
    assert perf["audio_source"] == "dQw4w9WgXcQ" and perf["opus"]["slug"] == etude["slug"]
    # a piece that isn't on the site, with the recording uploaded
    audio = upload(performer, "chopin.mp3", b"ID3 fake", "audio/mpeg", "audio")
    other = client.post("/api/performances", headers=performer, json={
        "title": "Баллада №1", "composer_name": "Фредерик Шопен", "audio_type": "hosted_file", "audio_source": audio["key"],
    }).json()
    assert other["audio_url"].endswith(".mp3")
    # someone else's file can't be used
    other_performer = register("petr_cello", role="performer")
    stolen = client.post("/api/performances", headers=other_performer, json={
        "title": "Кража", "audio_type": "hosted_file", "audio_source": audio["key"],
    })
    assert stolen.status_code == 422
    # a composer (even an administrator) doesn't publish performances; a work from the site gives its title
    assert client.post("/api/performances", headers=admin, json=body).status_code == 403
    assert perf["title"] == "Этюд" and perf["composer_name"] is None
    assert client.get("/api/performances", params={"opus": etude["slug"]}).json()["total"] == 1
    assert client.get("/api/performances", params={"performer": "vera_violin"}).json()["total"] == 2
    assert client.get("/api/users/vera_violin").json()["stats"]["performances"] == 2
    assert client.patch(f"/api/performances/{other['id']}", headers=admin, json={"title": "x"}).status_code == 404
    assert client.patch(f"/api/performances/{other['id']}", headers=performer, json={"recorded_year": 2025}).json()["recorded_year"] == 2025
    assert client.delete(f"/api/performances/{other['id']}", headers=performer).status_code == 204


def test_replaced_file_is_removed_only_after_saving(admin):
    """The old score is deleted once the change is committed; a failed change keeps it"""
    from allegro.core.storage import storage
    first = upload(admin, "a.pdf", b"%PDF-1.4 a", "application/pdf", "score")
    second = upload(admin, "b.pdf", b"%PDF-1.4 b", "application/pdf", "score")
    opus = create_opus(admin, title="Соната", score_file_key=first["key"], score_page_count=1)
    # an invalid change (a marker past the last page) is rejected: nothing is deleted
    r = client.patch(f"/api/opuses/{opus['slug']}", headers=admin, json={"score_file_key": second["key"], "markers": [{"page_number": 5, "timestamp_seconds": 0}]})
    assert r.status_code == 422 and storage.exists(first["key"])
    assert client.patch(f"/api/opuses/{opus['slug']}", headers=admin, json={"score_file_key": second["key"]}).status_code == 200
    assert not storage.exists(first["key"]) and storage.exists(second["key"])


# ---------------------------------------------------------------- site pages and suggestions

def test_about_page_is_written_by_administrators(admin, listener):
    assert "Сообщество" in client.get("/api/site/pages/about").json()["content_md"]  # a default text
    assert client.put("/api/site/pages/about", headers=listener, json={"content_md": "x"}).status_code == 403
    assert client.put("/api/site/pages/links", headers=admin, json={"content_md": "- [YouTube](https://youtube.com)"}).status_code == 200
    assert "YouTube" in client.get("/api/site/pages/links").json()["content_md"]
    assert client.get("/api/site/pages/secret").status_code == 422


def test_suggestions(admin, listener, theorist):
    assert client.post("/api/feedback", json={"title": "Тёмная тема", "body": "..."}).status_code == 401
    idea = client.post("/api/feedback", headers=listener, json={"kind": "idea", "title": "Ноты в MIDI", "body": "Хочу скачивать MIDI"}).json()
    assert idea["status"] == "new" and idea["author"]["username"] == "sam_listens"
    assert client.patch(f"/api/feedback/{idea['id']}", headers=theorist, json={"status": "done"}).status_code == 403
    answered = client.patch(f"/api/feedback/{idea['id']}", headers=admin, json={"status": "planned", "reply_md": "Сделаем!"}).json()
    assert answered["status"] == "planned" and answered["replied_at"]
    listing = client.get("/api/feedback").json()
    assert listing["total"] >= 1 and listing["items"][0]["reply_md"] == "Сделаем!"
    assert client.get("/api/feedback", params={"status": "planned"}).json()["total"] == 1
    # answered: the author can no longer take it back, an administrator can
    assert client.delete(f"/api/feedback/{idea['id']}", headers=listener).status_code == 403
    assert client.delete(f"/api/feedback/{idea['id']}", headers=admin).status_code == 204


def test_flood_protection(monkeypatch):
    """One address can't flood the site with changes or searches"""
    from allegro import main
    from allegro.core.ratelimit import RequestLimiter
    monkeypatch.setattr(main, "SEARCH_LIMIT", RequestLimiter(per_minute=3))
    codes = [client.get("/api/search", params={"q": "трио"}).status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3:] == [429, 429]
    r = client.get("/api/search", params={"q": "трио"})
    assert r.headers["retry-after"] == "60" and "Подождите" in r.json()["detail"]
    assert client.get("/api/opuses").status_code == 200  # reading pages is not limited


def test_new_password_signs_out_other_devices():
    phone = register("olga_harp", role="performer")
    laptop = login("olga_harp")
    r = client.post("/api/users/me/password", headers=laptop, json={"current_password": "secret-pass", "new_password": "another-pass"})
    assert r.status_code == 200
    fresh = {"Authorization": f"Bearer {token_of(r)}"}
    assert client.get("/api/auth/me", headers=phone).status_code == 401  # the other device is signed out
    assert client.get("/api/auth/me", headers=fresh).status_code == 200
    r = client.post("/api/users/me/sessions/revoke", headers=fresh)
    assert client.get("/api/auth/me", headers=fresh).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_of(r)}"}).status_code == 200
    set_user("olga_harp", is_hidden=True)


def test_feed_brings_every_hall_together(admin, theorist):
    """The main page is a feed: works, performances, articles and posts of all members, newest first"""
    create_opus(admin, title="Ноктюрн для ленты", genre="solo")
    client.post("/api/posts", headers=theorist, json={"kind": "article", "title": "Статья для ленты", "content_md": "Текст"})
    client.post("/api/posts", headers=theorist, json={"kind": "note", "content_md": "Запись для ленты"})
    page = client.get("/api/feed", params={"limit": 3}).json()
    assert [i["type"] for i in page["items"]] == ["post", "post", "opus"]
    assert page["items"][0]["post"]["content_md"] == "Запись для ленты"
    assert page["items"][0]["post"]["author"]["username"] == "ivan_theory"
    assert page["items"][2]["opus"]["author"]["username"] == "mira"
    # the next page continues where this one ended
    more = client.get("/api/feed", params={"limit": 3, "before": page["next_before"]}).json()
    assert more["items"] and all(i["created_at"] < page["items"][-1]["created_at"] for i in more["items"])
    works = client.get("/api/feed", params={"kind": "works"}).json()["items"]
    assert works and all(i["type"] == "opus" for i in works)
    blogs = client.get("/api/feed", params={"kind": "blogs"}).json()["items"]
    assert all(i["type"] == "post" and i["post"]["kind"] == "note" for i in blogs)


def test_hall_address_explains_what_is_wrong(admin):
    def check(value):
        return client.get("/api/auth/username", params={"value": value}).json()

    ok = check("Anna.Viola")
    assert ok["ok"] and ok["problems"] == []
    russian = check("Иван Петров")
    assert not russian["ok"] and any("латиница" in p for p in russian["problems"]) and any("Пробелы" in p for p in russian["problems"])
    assert russian["suggestions"][0] == "ivan_petrov"
    assert "ещё 1 символ" in check("ab")["problems"][0]
    assert "!" in check("ivan!")["problems"][0]
    taken = check("mira")
    assert taken["problems"] == ["Этот адрес уже занят"] and taken["suggestions"][0] == "mira1"
    # the same words come back when signing up with a wrong address
    r = client.post("/api/auth/register", json={"username": "Мира", "password": "secret-pass", "display_name": "М", "role": "listener"})
    assert r.status_code == 422 and "латиница" in r.text
