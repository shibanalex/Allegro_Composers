"""
API tests for the Allegro platform: the whole application (allegro.main), through its HTTP API.

Run from backend/:  python -m pytest tests/test_platform.py
"""
import pytest

from tests.support import PDF, client, create_opus, picture, register, upload


@pytest.fixture(scope="module")
def alice():
    return register("alice", "Алиса Композиторова")


@pytest.fixture(scope="module")
def bob():
    return register("bob", "Борис Теоретик")


# ---------------------------------------------------------------- identity

def test_health():
    assert client.get("/health").json()["status"] == "healthy"


def test_register_login_me(alice):
    assert client.get("/api/auth/me", headers=alice).json()["username"] == "alice"
    r = client.post("/api/auth/login", json={"login": "ALICE@example.com", "password": "secret-pass"})
    assert r.status_code == 200 and r.json()["user"]["username"] == "alice"
    assert client.post("/api/auth/login", json={"login": "alice", "password": "wrong-pass"}).status_code == 401


def test_register_validation(alice):
    base = {"email": "x@example.com", "password": "secret-pass", "display_name": "X"}
    assert client.post("/api/auth/register", json={**base, "username": "alice"}).status_code == 409
    assert client.post("/api/auth/register", json={**base, "username": "Кириллица"}).status_code == 422
    assert client.post("/api/auth/register", json={**base, "username": "admin"}).status_code == 422
    assert client.post("/api/auth/register", json={**base, "username": "shortpw", "password": "123"}).status_code == 422


def test_profile_update_and_public_page(alice):
    r = client.patch("/api/users/me", headers=alice, json={
        "pseudonym": "Allegro Cantabile", "bio": "Композитор, исследователь полифонии",
        "links": [{"label": "YouTube", "url": "https://youtube.com/@alice"}],
    })
    assert r.status_code == 200
    bad_link = client.patch("/api/users/me", headers=alice, json={"links": [{"label": "x", "url": "javascript:alert(1)"}]})
    assert bad_link.status_code == 422
    profile = client.get("/api/users/alice").json()
    assert profile["pseudonym"] == "Allegro Cantabile"
    assert "email" not in profile
    assert profile["stats"] == {"opuses": 0, "performances": 0, "posts": 0, "articles": 0}
    assert profile["role"] == "composer" and profile["hall_theme"] == "romantic"
    assert client.get("/api/users/nobody").status_code == 404


# ---------------------------------------------------------------- media

def test_media_upload_rules(alice):
    assert client.post("/api/media", files={"files": ("a.pdf", PDF, "application/pdf")}).status_code == 401
    wrong = client.post("/api/media", headers=alice, data={"purpose": "score"}, files={"files": ("a.mp3", b"x", "audio/mpeg")})
    assert wrong.status_code == 415
    score = upload(alice, "trio.pdf", PDF, "application/pdf", "score")
    assert score["key"].startswith("scores/alice/")
    assert client.get(score["url"]).content == PDF


def test_pictures_get_previews_and_covers_become_square(alice):
    import io

    from PIL import Image

    from allegro.core.storage import storage
    size = lambda url: Image.open(io.BytesIO(client.get(url).content)).size  # noqa: E731

    photo = upload(alice, "wide.jpg", picture(3000, 1500, "JPEG"), "image/jpeg", "image")
    assert photo["key"].endswith("_wide.jpg") and size(photo["url"]) == (3000, 1500)  # the original is kept
    assert photo["preview_url"] == photo["url"] + ".preview.webp" and size(photo["preview_url"]) == (800, 400)

    cover = upload(alice, "cover.png", picture(1200, 700), "image/png", "cover")
    assert cover["key"].startswith("covers/alice/") and cover["key"].endswith(".webp")
    assert size(cover["url"]) == (700, 700) and size(cover["preview_url"]) == (700, 700)

    # a file that only pretends to be a picture, and a decompression bomb, are refused
    fake = client.post("/api/media", headers=alice, data={"purpose": "image"}, files={"files": ("x.png", b"\x89PNG fake", "image/png")})
    assert fake.status_code == 415
    bomb = client.post("/api/media", headers=alice, data={"purpose": "image"}, files={"files": ("b.png", picture(7000, 6000), "image/png")})
    assert bomb.status_code == 415

    # deleting the work removes the cover together with its preview
    opus = create_opus(alice, title="С обложкой", cover_url=cover["url"])
    assert client.delete(f"/api/opuses/{opus['slug']}", headers=alice).status_code == 204
    assert not storage.exists(cover["key"]) and not storage.exists(cover["key"] + ".preview.webp")


# ---------------------------------------------------------------- catalog

def test_opus_lifecycle(alice, bob):
    score = upload(alice, "trio.pdf", PDF, "application/pdf", "score")
    audio = upload(alice, "trio.wav", b"RIFF....WAVE", "audio/wav", "audio")
    opus = create_opus(
        alice, subtitle="op. 1, Ч. I: Allegro", key_signature="ре минор", difficulty=4,
        tags=["Фортепиано", "скрипка", "фортепиано"], instrumentation="Ф-но, Скрипка, Вч.",
        audio_type="hosted_file", audio_source=audio["key"], audio_duration_seconds=90,
        score_file_key=score["key"], score_page_count=3,
        markers=[{"page_number": 2, "timestamp_seconds": 30}, {"page_number": 1, "timestamp_seconds": 0}],
    )
    assert opus["slug"] == "trio-re-minor"
    assert opus["tags"] == ["фортепиано", "скрипка"]
    assert [m["page_number"] for m in opus["markers"]] == [1, 2]
    assert opus["audio_url"] == audio["url"] and opus["score_url"] == score["url"]
    assert opus["author"]["username"] == "alice"

    # Markers are validated against the score
    slug = opus["slug"]
    bad = client.put(f"/api/opuses/{slug}/markers", headers=alice, json=[{"page_number": 5, "timestamp_seconds": 1}])
    assert bad.status_code == 422
    dup = client.put(f"/api/opuses/{slug}/markers", headers=alice, json=[{"page_number": 1, "timestamp_seconds": 1}] * 2)
    assert dup.status_code == 422
    ok = client.put(f"/api/opuses/{slug}/markers", headers=alice, json=[
        {"page_number": 1, "timestamp_seconds": 0}, {"page_number": 2, "timestamp_seconds": 28.5}, {"page_number": 3, "timestamp_seconds": 61},
    ])
    assert ok.status_code == 200 and len(ok.json()) == 3

    # Only the author edits
    assert client.patch(f"/api/opuses/{slug}", headers=bob, json={"title": "Моё!"}).status_code == 403
    r = client.patch(f"/api/opuses/{slug}", headers=alice, json={"audio_type": "youtube", "audio_source": "https://youtu.be/dQw4w9WgXcQ?t=5"})
    assert r.json()["audio_source"] == "dQw4w9WgXcQ" and r.json()["audio_url"] is None

    # Score download honours the author's choice
    assert client.get(f"/api/opuses/{slug}/score").content == PDF
    client.patch(f"/api/opuses/{slug}", headers=alice, json={"score_access": "view_only"})
    assert client.get(f"/api/opuses/{slug}/score", headers=bob).status_code == 403
    assert client.get(f"/api/opuses/{slug}/score", headers=alice).status_code == 200

    assert client.post(f"/api/opuses/{slug}/play").status_code == 204
    assert client.get(f"/api/opuses/{slug}").json()["play_count"] == 1


def test_youtube_validation(alice):
    r = client.post("/api/opuses", headers=alice, json={
        "title": "X", "ensemble": "solo", "form": "miniature", "audio_type": "youtube", "audio_source": "not a link",
    })
    assert r.status_code == 422
    assert client.post("/api/opuses", headers=alice, json={"title": "X", "ensemble": "band", "form": "sonata"}).status_code == 422


def test_library_filters_and_drafts(alice, bob):
    create_opus(bob, title="Прелюдия до мажор", ensemble="solo", form="miniature", key_signature="до мажор", difficulty=2, tags=["фортепиано"])
    create_opus(bob, title="Хорал", ensemble="choir", form="cantata", tags=["хор"])
    create_opus(bob, title="Черновик сюиты", ensemble="orchestra", form="suite", status="draft")

    def titles(**params):
        return {o["title"] for o in client.get("/api/opuses", params={"limit": 100, **params}).json()["items"]}

    assert "Черновик сюиты" not in titles()
    assert titles(ensemble="solo") == {"Прелюдия до мажор"}
    assert titles(form="cantata") == {"Хорал"}
    assert titles(key="до мажор", difficulty=2) == {"Прелюдия до мажор"}
    assert titles(tag="Фортепиано") >= {"Прелюдия до мажор", "Трио ре минор"}
    assert titles(q="ТРИО") == {"Трио ре минор"}  # case-insensitive Cyrillic
    assert titles(q="теоретик") == {"Прелюдия до мажор", "Хорал"}  # by author name
    assert titles(author="bob") == {"Прелюдия до мажор", "Хорал"}

    mine = client.get("/api/opuses", headers=bob, params={"mine": True}).json()
    assert {o["status"] for o in mine["items"]} == {"published", "draft"}
    draft_slug = next(o["slug"] for o in mine["items"] if o["status"] == "draft")
    assert client.get(f"/api/opuses/{draft_slug}").status_code == 404
    assert client.get(f"/api/opuses/{draft_slug}", headers=bob).status_code == 200

    facets = client.get("/api/library/facets").json()
    counts = {f["value"]: f["count"] for f in facets["ensembles"]}
    assert counts["solo"] == 1 and counts["orchestra"] == 0  # drafts are not counted
    assert {"value": "фортепиано", "label": "фортепиано", "count": 2} in facets["tags"]


def test_collections(alice, bob):
    own = create_opus(alice, title="Флориография I", ensemble="solo", form="miniature")
    foreign = client.get("/api/opuses", params={"author": "bob"}).json()["items"][0]
    rejected = client.post("/api/collections", headers=alice, json={"title": "Цикл", "opus_ids": [foreign["id"]]})
    assert rejected.status_code == 422
    r = client.post("/api/collections", headers=alice, json={"title": "Цикл «Флориография»", "year": 2026, "opus_ids": [own["id"]]})
    assert r.status_code == 201
    collections = client.get("/api/collections", params={"author": "alice"}).json()
    assert collections[0]["title"] == "Цикл «Флориография»"
    assert [o["title"] for o in collections[0]["opuses"]] == ["Флориография I"]
    assert client.delete(f"/api/collections/{r.json()['id']}", headers=bob).status_code == 404


def test_search(alice):
    result = client.get("/api/search", params={"q": "фортеп"}).json()
    assert "фортепиано" in result["tags"]
    assert {o["title"] for o in result["opuses"]} >= {"Трио ре минор"}
    composers = client.get("/api/search", params={"q": "алиса"}).json()["composers"]
    assert composers[0]["username"] == "alice"


# ---------------------------------------------------------------- content & discussion

def test_posts_and_workshop(alice, bob):
    opus = client.get("/api/opuses/trio-re-minor").json()
    r = client.post("/api/posts", headers=alice, json={
        "kind": "workshop", "title": "Не проседает ли фактура?", "content_md": "Послушайте экспозицию", "opus_id": opus["id"],
    })
    assert r.status_code == 201
    post = r.json()
    assert post["opus"]["slug"] == "trio-re-minor"
    client.post("/api/posts", headers=bob, json={"kind": "article", "title": "Терцовые соотношения", "content_md": "# Анализ"})

    kinds = {p["kind"] for p in client.get("/api/posts", params={"kind": ["article", "workshop"]}).json()["items"]}
    assert kinds == {"article", "workshop"}
    assert client.get("/api/posts", params={"kind": "article"}).json()["total"] == 1
    assert client.get(f"/api/posts/{post['slug']}").json()["view_count"] == 1
    assert client.patch(f"/api/posts/{post['slug']}", headers=bob, json={"title": "x"}).status_code == 403


def test_critiques_with_timecodes(alice, bob):
    opus = client.get("/api/opuses/trio-re-minor").json()
    r = client.post("/api/comments", headers=bob, json={
        "opus_id": opus["id"], "timestamp_marker": 135, "content_md": "Вот здесь, 02:15, терцдецимаккорд перегружен в басу",
    })
    assert r.status_code == 201
    critique = r.json()
    reply = client.post("/api/comments", headers=alice, json={"opus_id": opus["id"], "parent_id": critique["id"], "content_md": "Согласна"})
    assert reply.status_code == 201

    workshop = client.get("/api/posts", params={"kind": "workshop"}).json()["items"][0]
    wrong_parent = client.post("/api/comments", headers=bob, json={"post_id": workshop["id"], "parent_id": critique["id"], "content_md": "x"})
    assert wrong_parent.status_code == 422
    # Workshop thread about an opus accepts timecodes; an article without a recording does not
    assert client.post("/api/comments", headers=bob, json={"post_id": workshop["id"], "timestamp_marker": 10, "content_md": "ок"}).status_code == 201
    article = client.get("/api/posts", params={"kind": "article"}).json()["items"][0]
    assert client.post("/api/comments", headers=alice, json={"post_id": article["id"], "timestamp_marker": 10, "content_md": "x"}).status_code == 422
    assert client.post("/api/comments", json={"opus_id": opus["id"], "content_md": "anon"}).status_code == 401

    thread = client.get("/api/comments", params={"opus_id": opus["id"]}).json()
    assert [c["timestamp_marker"] for c in thread] == [135, None]
    assert thread[1]["parent_id"] == critique["id"]
    assert client.get("/api/opuses/trio-re-minor").json()["critique_count"] == 2

    # The opus author can moderate; replies are removed with the parent
    assert client.delete(f"/api/comments/{reply.json()['id']}", headers=bob).status_code == 403
    assert client.delete(f"/api/comments/{critique['id']}", headers=alice).status_code == 204
    assert client.get("/api/comments", params={"opus_id": opus["id"]}).json() == []


def test_delete_opus_cleans_up(alice):
    score = upload(alice, "tmp.pdf", PDF, "application/pdf", "score")
    opus = create_opus(alice, title="Временный", score_file_key=score["key"], score_page_count=1)
    assert client.delete(f"/api/opuses/{opus['slug']}", headers=alice).status_code == 204
    assert client.get(score["url"]).status_code == 404


# ---------------------------------------------------------------- MusicXML

MUSICXML = b'<?xml version="1.0"?><score-partwise version="4.0"><part-list/></score-partwise>'


def test_musicxml_upload_is_validated_by_content(alice):
    ok = upload(alice, "trio.musicxml", MUSICXML, "application/octet-stream", "musicxml")
    assert ok["key"].startswith("musicxmls/alice/")
    assert upload(alice, "trio.mxl", b"PK\x03\x04zip", "", "musicxml")["name"] == "trio.mxl"
    fake = client.post("/api/media", headers=alice, data={"purpose": "musicxml"}, files={"files": ("x.xml", b"<html/>", "text/xml")})
    assert fake.status_code == 415
    wrong_ext = client.post("/api/media", headers=alice, data={"purpose": "musicxml"}, files={"files": ("x.pdf", MUSICXML, "application/pdf")})
    assert wrong_ext.status_code == 415


def test_opus_with_musicxml_cursor_sync(alice, bob):
    xml = upload(alice, "prelude.musicxml", MUSICXML, "text/xml", "musicxml")
    opus = create_opus(
        alice, title="Прелюдия с курсором", ensemble="solo", form="miniature",
        musicxml_file_key=xml["key"], audio_offset_seconds=1.5,
        measure_markers=[{"measure_number": 9, "timestamp_seconds": 20}, {"measure_number": 1, "timestamp_seconds": 1.5}],
    )
    assert opus["musicxml_url"] == xml["url"] and opus["audio_offset_seconds"] == 1.5
    assert [m["measure_number"] for m in opus["measure_markers"]] == [1, 9]

    slug = opus["slug"]
    backwards = client.put(f"/api/opuses/{slug}/measure-markers", headers=alice, json=[
        {"measure_number": 1, "timestamp_seconds": 10}, {"measure_number": 5, "timestamp_seconds": 4},
    ])
    assert backwards.status_code == 422  # later measure can't start earlier
    assert client.put(f"/api/opuses/{slug}/measure-markers", headers=bob, json=[]).status_code == 403

    assert client.get(f"/api/opuses/{slug}/musicxml").content == MUSICXML
    client.patch(f"/api/opuses/{slug}", headers=alice, json={"score_access": "view_only"})
    assert client.get(f"/api/opuses/{slug}/musicxml", headers=bob).status_code == 403

    # Replacing the file removes the old one from storage
    newer = upload(alice, "prelude-v2.musicxml", MUSICXML, "text/xml", "musicxml")
    client.patch(f"/api/opuses/{slug}", headers=alice, json={"musicxml_file_key": newer["key"]})
    assert client.get(xml["url"]).status_code == 404


def test_pdf_pages_follow_musicxml_page_breaks(alice):
    # 4/4 at 120 bpm → 2 s per measure; page 2 starts at measure 3 (a MuseScore-style page break)
    measure = '<measure number="{n}">{extra}<note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note></measure>'
    first = '<attributes><divisions>1</divisions><time><beats>4</beats><beat-type>4</beat-type></time></attributes><direction><sound tempo="120"/></direction>'
    body = "".join(measure.format(n=n, extra=first if n == 1 else ('<print new-page="yes"/>' if n == 3 else "")) for n in range(1, 5))
    xml = f'<score-partwise version="4.0"><part-list><score-part id="P1"><part-name>P</part-name></score-part></part-list><part id="P1">{body}</part></score-partwise>'.encode()
    xml_up = upload(alice, "auto.musicxml", xml, "text/xml", "musicxml")
    pdf_up = upload(alice, "auto.pdf", PDF, "application/pdf", "score")
    wav = upload(alice, "auto.wav", b"RIFF....WAVE", "audio/wav", "audio")
    opus = create_opus(
        alice, title="Автолистание", musicxml_file_key=xml_up["key"], score_file_key=pdf_up["key"], score_page_count=2,
        audio_type="hosted_file", audio_source=wav["key"], audio_offset_seconds=1,
    )
    assert opus["auto_page_markers"] is True
    assert [(m["page_number"], m["timestamp_seconds"]) for m in opus["markers"]] == [(1, 1.0), (2, 5.0)]

    # Measure markers (rubato) move the page turn too: measure 3 pinned at 9 s
    r = client.put(f"/api/opuses/{opus['slug']}/measure-markers", headers=alice, json=[
        {"measure_number": 1, "timestamp_seconds": 1}, {"measure_number": 3, "timestamp_seconds": 9},
    ])
    assert r.status_code == 200
    assert client.get(f"/api/opuses/{opus['slug']}").json()["markers"][1]["timestamp_seconds"] == 9.0

    # Hand-set markers switch auto mode off; an empty list switches it back on
    manual = client.patch(f"/api/opuses/{opus['slug']}", headers=alice, json={"markers": [{"page_number": 1, "timestamp_seconds": 0}, {"page_number": 2, "timestamp_seconds": 3}]})
    assert manual.json()["auto_page_markers"] is False and manual.json()["markers"][1]["timestamp_seconds"] == 3
    back = client.patch(f"/api/opuses/{opus['slug']}", headers=alice, json={"markers": []})
    assert back.json()["auto_page_markers"] is True and back.json()["markers"][1]["timestamp_seconds"] == 9.0


# ---------------------------------------------------------------- composer hall: blog & materials

def test_blog_posts_like_a_channel(alice, bob):
    short = client.post("/api/posts", headers=alice, json={"kind": "note", "content_md": "Сегодня дописал коду. Завтра — запись."})
    assert short.status_code == 201 and short.json()["title"] == ""
    photo = upload(alice, "desk.png", picture(), "image/png", "image")
    media_only = client.post("/api/posts", headers=alice, json={"kind": "note", "attachments": [
        {"url": photo["url"], "name": "desk.png", "content_type": "image/png", "size": 4}]})
    assert media_only.status_code == 201
    assert client.post("/api/posts", headers=alice, json={"kind": "note", "content_md": "  "}).status_code == 422
    assert client.post("/api/posts", headers=alice, json={"kind": "article", "content_md": "без заголовка"}).status_code == 422
    channel = client.get("/api/posts", params={"author": "alice", "kind": "note"}).json()["items"]
    assert channel[0]["id"] == media_only.json()["id"]  # newest first


def test_materials(alice, bob):
    assert client.post("/api/materials", headers=alice, json={"kind": "link", "title": "IMSLP"}).status_code == 422
    assert client.post("/api/materials", headers=alice, json={"kind": "link", "title": "X", "url": "javascript:alert(1)"}).status_code == 422
    link = client.post("/api/materials", headers=alice, json={"kind": "link", "title": "IMSLP", "url": "https://imslp.org"})
    assert link.status_code == 201
    doc = upload(alice, "harmony.pdf", PDF, "application/pdf", "attachment")
    book = client.post("/api/materials", headers=alice, json={
        "kind": "book", "title": "Учебник гармонии", "description": "Мой конспект",
        "file": {"url": doc["url"], "name": "harmony.pdf", "content_type": "application/pdf", "size": doc["size"]},
    })
    assert book.status_code == 201
    listed = client.get("/api/materials", params={"author": "alice"}).json()
    assert {m["kind"] for m in listed} == {"link", "book"}
    assert client.delete(f"/api/materials/{book.json()['id']}", headers=bob).status_code == 404
    assert client.delete(f"/api/materials/{book.json()['id']}", headers=alice).status_code == 204
    assert client.get(doc["url"]).status_code == 404  # file removed with the material


# ---------------------------------------------------------------- invite-only mode & shadowed accounts

def _set_hidden(username, hidden):
    from allegro.core.db import SessionLocal
    from allegro.modules.accounts.models import User
    with SessionLocal() as db:
        db.query(User).filter(User.username == username).update({"is_hidden": hidden})
        db.commit()


def test_shadowed_account_vanishes_but_is_kept(alice, bob):
    bob_opus = client.get("/api/opuses", params={"author": "bob"}).json()["items"][0]
    trio = client.get("/api/opuses/trio-re-minor").json()
    client.post("/api/comments", headers=bob, json={"opus_id": trio["id"], "content_md": "Тень проверяет"})
    _set_hidden("bob", True)
    try:
        assert client.get("/api/users/bob").status_code == 404
        assert "bob" not in [u["username"] for u in client.get("/api/users").json()]
        assert client.get(f"/api/opuses/{bob_opus['slug']}").status_code == 404
        assert all(o["author"]["username"] != "bob" for o in client.get("/api/opuses", params={"limit": 100}).json()["items"])
        assert client.get("/api/posts", params={"author": "bob"}).json()["total"] == 0
        assert not client.get("/api/search", params={"q": "борис"}).json()["composers"]
        assert all(c["author"]["username"] != "bob" for c in client.get("/api/comments", params={"opus_id": trio["id"]}).json())
        assert client.get("/api/auth/me", headers=bob).status_code == 401  # old token no longer works
        assert client.post("/api/auth/login", json={"login": "bob", "password": "secret-pass"}).status_code == 403
    finally:
        _set_hidden("bob", False)
    assert client.get("/api/users/bob").status_code == 200  # back from the shadow, nothing lost
    assert "bob" in [u["username"] for u in client.get("/api/users").json()]


def test_ownership_of_uploaded_files(alice, bob):
    """Nobody can attach someone else's upload: steal a paid score through their own opus, or delete it"""
    from allegro.core.storage import storage
    pdf = upload(alice, "trio.pdf", PDF, "application/pdf", "score")
    r = client.post("/api/opuses", headers=bob, json={"title": "Чужое", "ensemble": "solo", "form": "other", "score_file_key": pdf["key"]})
    assert r.status_code == 422
    r = client.post("/api/posts", headers=bob, json={"kind": "note", "content_md": "x", "attachments": [{"url": "javascript:alert(1)", "name": "a"}]})
    assert r.status_code == 422
    r = client.post("/api/materials", headers=bob, json={"kind": "book", "title": "b", "cover_url": pdf["url"]})
    assert r.status_code == 422
    assert storage.exists(pdf["key"])
    # scripts in disguise are refused
    for name, ct, purpose in [("x.html", "text/html", "attachment"), ("x.svg", "image/svg+xml", "image"), ("x.pdf", "application/pdf", "score")]:
        r = client.post("/api/media", headers=alice, data={"purpose": purpose}, files={"files": (name, b"<script>", ct)})
        assert r.status_code == 415, name


def test_first_setup_creates_the_only_owner(alice, monkeypatch):
    from allegro.core.config import settings
    from allegro.modules.accounts import service
    body = {"code": "a-long-setup-code-123", "username": "owner", "email": "owner@example.com",
            "password": "a-very-long-password", "display_name": "Owner"}
    monkeypatch.setattr(settings, "setup_token", "a-long-setup-code-123")
    # users already exist: setup is closed for good
    assert client.get("/api/auth/config").json()["setup_available"] is False
    assert client.post("/api/auth/setup", json=body).status_code == 404
    # on a fresh database
    monkeypatch.setattr(service, "setup_available", lambda db: True)
    assert client.post("/api/auth/setup", json={**body, "code": "wrong-code-wrong-code"}).status_code == 403
    assert client.post("/api/auth/setup", json={**body, "password": "short-pass"}).status_code == 422
    r = client.post("/api/auth/setup", json=body)
    assert r.status_code == 201, r.text
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"}).json()
    assert me["username"] == "owner" and me["is_admin"] is True and "manage_site" in me["capabilities"]


def test_search_by_words_in_texts(alice):
    """Untitled blog posts are found by the words of their text, whatever the ending; every word must match"""
    client.post("/api/posts", headers=alice, json={"kind": "note", "content_md": "Наконец пришла книга по **полифонии** (Григорьев). Партитурная бумага тоже пришла."})
    client.post("/api/posts", headers=alice, json={"kind": "note", "content_md": "Сегодня сходил в поле, ёлки в снегу"})
    found = client.get("/api/search", params={"q": "полифония книги"}).json()
    assert len(found["posts"]) == 1
    post = found["posts"][0]
    assert post["title"] == "" and "полифонии" in post["snippet"] and "**" not in post["snippet"]
    assert client.get("/api/search", params={"q": "полифония космос"}).json()["posts"] == []  # all words must be there
    assert len(client.get("/api/search", params={"q": "елки"}).json()["posts"]) == 1  # ё = е
    assert client.get("/api/search", params={"q": "%"}).json()["posts"] == []  # no wildcards, no crash
