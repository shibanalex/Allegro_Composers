"""The login cookie, CSRF, and what an uploaded file or a text field can and can't do"""
import pytest

from tests.support import client, register, set_user, token_of

MEMBERS = ["cookie_owner"]


@pytest.fixture(scope="module", autouse=True)
def _leave_no_trace():
    yield
    for username in MEMBERS:
        set_user(username, is_hidden=True)


@pytest.fixture(scope="module")
def signed_in():
    """The raw sign-up answer: its cookie is what a browser keeps"""
    register("cookie_owner", "Кука")
    r = client.post("/api/auth/login", json={"login": "cookie_owner", "password": "secret-pass"})
    assert r.status_code == 200
    return r


def test_the_token_lives_in_an_httponly_cookie_only(signed_in):
    assert "access_token" not in signed_in.json()  # a script injected into a page could read the answer
    cookie = next(h for h in signed_in.headers.get_list("set-cookie") if h.startswith("allegro_token="))
    assert "HttpOnly" in cookie and "samesite=lax" in cookie.lower() and "Max-Age=" in cookie
    marker = next(h for h in signed_in.headers.get_list("set-cookie") if h.startswith("allegro_session="))
    assert "HttpOnly" not in marker and "allegro_session=1" in marker


def test_csrf_a_foreign_site_cannot_act_with_the_cookie(signed_in):
    jar = {"Cookie": f"allegro_token={token_of(signed_in)}"}
    note = {"kind": "note", "content_md": "Моя запись"}
    # reading with the cookie is fine
    assert client.get("/api/auth/me", headers=jar).json()["username"] == "cookie_owner"
    # a form or a script on another site: refused
    forged = client.post("/api/posts", json=note, headers={**jar, "Sec-Fetch-Site": "cross-site"})
    assert forged.status_code == 403
    old_browser = client.post("/api/posts", json=note, headers={**jar, "Origin": "https://evil.example"})
    assert old_browser.status_code == 403
    # the site's own pages: allowed
    own = client.post("/api/posts", json=note, headers={**jar, "Sec-Fetch-Site": "same-origin"})
    assert own.status_code == 201
    # the header (the site's server rendering, API clients) is not a cookie and can't be forged by a page
    header = client.post("/api/posts", json=note, headers={"Authorization": f"Bearer {token_of(signed_in)}", "Sec-Fetch-Site": "cross-site"})
    assert header.status_code == 201


def test_logout_removes_the_cookie():
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    gone = [h for h in r.headers.get_list("set-cookie") if h.startswith("allegro_token=")]
    assert gone and ("Max-Age=0" in gone[0] or "expires=Thu, 01 Jan 1970" in gone[0])


# ---------------------------------------------------------------- uploads: formats, count, the daily limit

def test_upload_limits(monkeypatch):
    from allegro.core.config import settings
    from allegro.core.storage import storage
    headers = register("upload_tester", "Загрузчик")
    MEMBERS.append("upload_tester")

    def send(files, purpose="attachment"):
        return client.post("/api/media", headers=headers, data={"purpose": purpose}, files=[("files", f) for f in files])

    # attachments: a list of what musicians share, nothing else
    assert send([("setup.exe", b"MZ", "application/octet-stream")]).status_code == 415
    assert send([("page.html", b"<script>", "text/html")]).status_code == 415
    assert send([("song.mid", b"MThd", "audio/midi")]).status_code == 201
    # no more than 10 files at once
    assert send([(f"n{i}.txt", b"x", "text/plain") for i in range(11)]).status_code == 422
    # the daily limit: the file that doesn't fit is refused and not kept
    monkeypatch.setattr(settings, "upload_daily_mb", 1)
    big = b"0" * (700 * 1024)
    first = send([("a.txt", big, "text/plain")])
    assert first.status_code == 201
    second = send([("b.txt", big, "text/plain")])
    assert second.status_code == 413 and "МБ в сутки" in second.json()["detail"]
    keys = list(storage.keys("attachments/upload_tester/"))
    assert not any(k.endswith("_b.txt") for k in keys)


def test_each_kind_of_file_has_its_own_size_limit(monkeypatch):
    from allegro.modules.media import service
    headers = register("size_tester", "Размер")
    MEMBERS.append("size_tester")
    assert client.get("/api/media/limits").json()["score"] == 50
    monkeypatch.setitem(service.LIMIT_MB, "score", 1)
    big_pdf = b"%PDF-1.4 " + b"0" * (1024 * 1024 + 10)
    r = client.post("/api/media", headers=headers, data={"purpose": "score"}, files={"files": ("big.pdf", big_pdf, "application/pdf")})
    assert r.status_code == 413 and "1 МБ" in r.json()["detail"]


def test_names_and_titles_are_cleaned():
    headers = register("clean_names", "Чистое Имя")
    MEMBERS.append("clean_names")

    def name(value):
        r = client.patch("/api/users/me", headers=headers, json={"display_name": value})
        return r.json()["display_name"] if r.status_code == 200 else r.json()["detail"]

    assert name("  Иван   Петров\n") == "Иван Петров"
    assert name("Иван‮вонаП") == "ИванвонаП"  # a direction override would show someone else's name
    assert name("​​") == "Имя: нужна хотя бы одна буква или цифра"
    assert name("   ") == "Имя: нужна хотя бы одна буква или цифра"
    assert name("A" * 121) == "Имя: не длиннее 120 знаков"
    opus = client.post("/api/opuses", headers=headers, json={"title": " Соната​  №1 ", "genre": "solo"}).json()
    assert opus["title"] == "Соната №1" and opus["slug"].startswith("sonata-1")



def test_onboarding_hints_are_remembered_in_the_account():
    headers = register("hint_reader", "Новичок")
    MEMBERS.append("hint_reader")
    assert client.get("/api/auth/me", headers=headers).json()["seen_hints"] == []
    for hints in (["feed"], ["feed", "create", "bell"]):
        assert client.post("/api/users/me/hints", json={"hints": hints}, headers=headers).status_code == 204
    assert client.get("/api/auth/me", headers=headers).json()["seen_hints"] == ["feed", "create", "bell"]
    assert client.post("/api/users/me/hints", json={"hints": ["<script>"]}, headers=headers).status_code == 422
    assert client.post("/api/users/me/hints", json={"hints": ["x"] * 101}, headers=headers).status_code == 422
    client.delete("/api/users/me/hints", headers=headers)
    assert client.get("/api/auth/me", headers=headers).json()["seen_hints"] == []
