"""Injection attempts against the API: SQL, LIKE wildcards, path traversal, stored markup, forged identifiers.

Every query goes through the ORM with bound parameters, so these mostly prove that nothing has slipped:
the payloads must come back as plain data, never change a query, a file path or a response header.
"""
import pytest

from tests.support import client, create_opus, register, set_user

MEMBERS = ["inj_author", "inj_other"]
SQL = ["' OR '1'='1", "'; DROP TABLE users; --", "\" OR 1=1 --", "1) UNION SELECT password_hash FROM users --", "%' --"]


@pytest.fixture(scope="module", autouse=True)
def _leave_no_trace():
    yield
    for username in MEMBERS:
        set_user(username, is_hidden=True)


@pytest.fixture(scope="module")
def author():
    return register("inj_author", "Автор Инъекций", role="composer")


def test_sql_in_every_search_and_filter_is_just_text(author):
    create_opus(author, title="Безобидная соната")
    total = client.get("/api/users", params={"limit": 100}).json()["total"]
    for payload in SQL:
        for path, params in (
            ("/api/search", {"q": payload}),
            ("/api/users", {"q": payload}),
            ("/api/users", {"role": payload}),
            ("/api/opuses", {"genre": payload}),
            ("/api/opuses", {"instrument": payload}),
            ("/api/opuses", {"key": payload}),
            ("/api/opuses", {"author": payload}),
            ("/api/posts", {"author": payload}),
            ("/api/feed", {"kind": payload}),
            ("/api/chat/messages", {"before": payload}),
        ):
            r = client.get(path, params=params)
            assert r.status_code in (200, 422), (path, payload, r.status_code)
            body = r.text.lower()  # a refusal may quote the input back; a database error must never show
            assert not any(leak in body for leak in ("syntax error", "sqlite", "psycopg", "sqlalchemy", "traceback"))
            if r.status_code == 200:
                assert "password_hash" not in body
    # the tables are all still there
    assert client.get("/api/users", params={"limit": 100}).json()["total"] == total


def test_like_wildcards_are_literal(author):
    """«%» is not a word and is dropped (no filter at all); «_» is matched as the character itself, not «any one»"""
    everyone = client.get("/api/users", params={"limit": 100}).json()
    assert client.get("/api/users", params={"q": "%", "limit": 100}).json()["total"] == everyone["total"]
    underscored = client.get("/api/users", params={"q": "_", "limit": 100}).json()["items"]
    assert underscored and all("_" in u["username"] or "_" in u["display_name"] or "_" in (u.get("pseudonym") or "")
                               or "_" in (u.get("bio") or "") for u in underscored)


def test_paths_out_of_the_storage_are_refused(author):
    for url in ("/media/../../backend/.env", "/media/audios/../../.env", "/media/%2e%2e/%2e%2e/etc/passwd",
                "/media/audios/inj_author/../../../../etc/passwd.mp3", "file:///etc/passwd", "../.env"):
        r = client.get("/api/media/peaks", params={"url": url})
        assert r.status_code in (400, 404, 422), (url, r.status_code)
        assert "SECRET" not in r.text and "root:" not in r.text
    for path in ("/media/..%2f..%2fbackend%2f.env", "/media/../allegro_platform.db"):
        r = client.get(path)
        assert r.status_code in (400, 404), (path, r.status_code)


def test_markup_is_stored_as_it_was_typed_and_never_runs_on_the_server(author):
    """The API keeps text as data (the site escapes it when showing); names lose control characters"""
    xss = '<script>alert(1)</script><img src=x onerror=alert(2)>'
    r = client.patch("/api/users/me", headers=author, json={"display_name": f"Автор {xss}"})
    assert r.status_code == 200
    assert r.json()["display_name"] == f"Автор {xss}"  # data, escaped by the site at display time
    r = client.post("/api/chat/messages", headers=author, json={"text": xss})
    assert r.status_code == 201 and r.json()["text"] == xss
    assert r.headers["content-type"].startswith("application/json")  # never served as a page
    client.patch("/api/users/me", headers=author, json={"display_name": "Автор Инъекций"})


def test_header_injection_through_names_and_slugs(author):
    opus = create_opus(author, title='Соната"\r\nSet-Cookie: pwned=1')
    assert "\r" not in opus["slug"] and "\n" not in opus["slug"] and '"' not in opus["slug"]
    r = client.get(f"/api/opuses/{opus['slug']}")
    assert "pwned" not in r.headers.get("set-cookie", "")


def test_a_youtube_source_must_be_a_video_id(author):
    for bad in ("javascript:1", "../../evil", '"><svg/on', "aaaaaaaaaa'"):
        r = client.post("/api/opuses", headers=author, json={"title": "Видео", "genre": "solo", "audio_type": "youtube", "audio_source": bad})
        assert r.status_code == 422, (bad, r.text)
    ok = client.post("/api/opuses", headers=author, json={
        "title": "Видео", "genre": "solo", "audio_type": "youtube", "audio_source": "https://youtu.be/dQw4w9WgXcQ"})
    assert ok.status_code == 201 and ok.json()["audio_source"] == "dQw4w9WgXcQ"


def test_forged_identifiers_and_mass_assignment(author):
    other = register("inj_other", "Другой")
    me = client.get("/api/auth/me", headers=author).json()
    # extra fields in a body are ignored: nobody makes themselves an administrator or someone else
    r = client.patch("/api/users/me", headers=author, json={"is_admin": True, "is_moderator": True, "id": "00000000-0000-0000-0000-000000000000",
                                                             "username": "inj_other", "seen_hints": ["x"] * 500})
    assert r.status_code in (200, 422)
    after = client.get("/api/auth/me", headers=author).json()
    assert after["is_admin"] is False and after.get("is_moderator") is False and after["id"] == me["id"]
    # a chat message can't be posted in someone else's name
    r = client.post("/api/chat/messages", headers=author, json={"text": "Я", "author_id": client.get("/api/auth/me", headers=other).json()["id"]})
    assert r.json()["author"]["username"] == "inj_author"
    # a forged login token is refused
    forged = "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiIxIn0."  # alg «none»
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_a_file_pretending_to_be_audio_cannot_steer_ffmpeg(author):
    """A playlist or concat script named .mp3 is not decoded: no fetching addresses, no reading other files"""
    from tests.support import upload
    from allegro.core import peaks
    for name, body in (("concat.mp3", b"ffconcat version 1.0\nfile '/etc/passwd'\n"),
                       ("playlist.ogg", b"#EXTM3U\n#EXTINF:5,\nhttp://127.0.0.1:8001/api/publish\n#EXT-X-ENDLIST\n")):
        item = upload(author, name, body, "audio/mpeg", "audio")
        assert client.get("/api/media/peaks", params={"url": item["url"]}).status_code == 404
        assert peaks.read(item["key"]) is None
