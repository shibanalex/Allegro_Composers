"""Likes, quotations and links between posts, moderation by capability, hall settings"""
import pytest

from tests.support import client, create_opus, login, picture, register, set_user, upload

MEMBERS = ["lina_notes", "oleg_listens", "rita_mod", "boris_comp"]


@pytest.fixture(scope="module", autouse=True)
def _leave_no_trace():
    """Other test files count works and posts on the same database: afterwards these members go in the shadow"""
    yield
    for username in MEMBERS:
        set_user(username, is_hidden=True)


@pytest.fixture(scope="module")
def author():
    return register("lina_notes", "Лина", role="theorist")


@pytest.fixture(scope="module")
def reader():
    return register("oleg_listens", "Олег", role="listener")


@pytest.fixture(scope="module")
def composer():
    return register("boris_comp", "Борис", role="composer")


def _post(headers, **body):
    r = client.post("/api/posts", headers=headers, json={"kind": "note", "content_md": "Запись", **body})
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- «нравится»

def test_likes_are_one_per_member_and_show_in_the_feed(author, reader):
    post = _post(author, content_md="Слушаю Шостаковича")
    url = f"/api/reactions/post/{post['id']}"
    assert client.put(url).status_code == 401
    assert client.put(url, headers=reader).json() == {"count": 1, "mine": True}
    assert client.put(url, headers=reader).json() == {"count": 1, "mine": True}  # twice is still one
    assert client.put(url, headers=author).json()["count"] == 2

    item = next(i for i in client.get("/api/feed", headers=reader).json()["items"] if i.get("post") and i["post"]["id"] == post["id"])
    assert item["likes"] == {"count": 2, "mine": True}
    anonymous = next(i for i in client.get("/api/feed").json()["items"] if i.get("post") and i["post"]["id"] == post["id"])
    assert anonymous["likes"] == {"count": 2, "mine": False}

    assert client.delete(url, headers=reader).json() == {"count": 1, "mine": False}
    batch = client.get("/api/reactions/post", params={"ids": post["id"]}, headers=author).json()
    assert batch[post["id"]] == {"count": 1, "mine": True}

    # likes of a deleted post go with it; unknown things can't be liked
    client.delete(f"/api/posts/{post['slug']}", headers=author)
    assert client.put(url, headers=reader).status_code == 404
    assert client.put(f"/api/reactions/comment/{post['id']}", headers=reader).status_code == 422


def test_works_can_be_liked(composer, reader):
    opus = create_opus(composer, title="Пассакалия", genre="solo")
    assert client.put(f"/api/reactions/opus/{opus['id']}", headers=reader).json() == {"count": 1, "mine": True}


# ---------------------------------------------------------------- posts refer to each other

def test_a_post_quotes_another(author, reader):
    original = _post(author, content_md="Фуга — это разговор голосов")
    quote = _post(reader, content_md="Точно сказано", quote_post_id=original["id"])
    bare = _post(reader, content_md="", quote_post_id=original["id"])  # a repost without words of one's own
    assert bare["content_md"] == "" and bare["quote"]["id"] == original["id"]
    assert quote["quote"]["slug"] == original["slug"] and quote["quote"]["preview"].startswith("Фуга")
    assert quote["quote"]["author"]["username"] == "lina_notes"

    draft = _post(author, content_md="Черновик", status="draft")
    r = client.post("/api/posts", headers=reader, json={"kind": "note", "content_md": "x", "quote_post_id": draft["id"]})
    assert r.status_code == 422
    # the quoted post disappears: the quotation stays, without it
    client.delete(f"/api/posts/{original['slug']}", headers=author)
    assert client.get(f"/api/posts/{quote['slug']}").json()["quote"] is None


def test_links_in_the_text_become_mentions(author, reader, composer):
    target = _post(author, title="О контрапункте", kind="article", content_md="Статья")
    opus = create_opus(composer, title="Инвенция", genre="solo")
    mention = _post(reader, content_md=f"Читайте [статью](/posts/{target['slug']}) и слушайте https://allegro.example/opus/{opus['slug']}")
    assert [p["slug"] for p in client.get(f"/api/mentions/post/{target['slug']}").json()] == [mention["slug"]]
    assert [p["slug"] for p in client.get(f"/api/mentions/opus/{opus['slug']}").json()] == [mention["slug"]]
    # an edited text forgets the old links
    client.patch(f"/api/posts/{mention['slug']}", headers=reader, json={"content_md": "Передумал"})
    assert client.get(f"/api/mentions/post/{target['slug']}").json() == []


# ---------------------------------------------------------------- roles and staff

def test_capability_matrix_and_moderators(author, reader):
    matrix = {row["capability"]: set(row["who"]) for row in client.get("/api/roles").json()}
    assert matrix["publish_opus"] == {"composer"}
    assert matrix["publish_article"] == {"composer", "theorist"}
    assert matrix["comment"] >= {"composer", "theorist", "performer", "listener"}
    assert "moderator" in matrix["moderate"] and "listener" not in matrix["moderate"]

    post = _post(author, content_md="Спорная мысль")
    comment = client.post("/api/comments", headers=reader, json={"post_id": post["id"], "content_md": "Грубость"}).json()
    rita = register("rita_mod", "Рита", role="listener")
    assert client.delete(f"/api/comments/{comment['id']}", headers=rita).status_code == 403
    assert client.delete(f"/api/posts/{post['slug']}", headers=rita).status_code == 403

    set_user("rita_mod", is_moderator=True)
    rita = login("rita_mod")
    assert "moderate" in client.get("/api/auth/me", headers=rita).json()["capabilities"]
    assert "invite" not in client.get("/api/auth/me", headers=rita).json()["capabilities"]
    assert client.get("/api/admin/links", headers=rita).status_code == 403
    assert client.delete(f"/api/comments/{comment['id']}", headers=rita).status_code == 204
    assert client.delete(f"/api/posts/{post['slug']}", headers=rita).status_code == 204


# ---------------------------------------------------------------- the hall

def test_hall_settings(author, reader):
    banner = upload(author, "hall.png", picture(1600, 500), "image/png", "image")
    body = {"hall": {"cover_url": banner["url"], "epigraph": "Музыка — это время", "epigraph_source": "Стравинский",
                     "accent": "crimson", "tabs": ["blog", "articles", "about", "blog"]}}
    r = client.patch("/api/users/me", headers=author, json=body)
    assert r.status_code == 200, r.text
    hall = client.get("/api/users/lina_notes").json()["hall"]
    assert hall["accent"] == "crimson" and hall["tabs"] == ["blog", "articles", "about"] and hall["epigraph"].startswith("Музыка")

    assert client.patch("/api/users/me", headers=author, json={"hall": {"accent": "neon"}}).status_code == 422
    assert client.patch("/api/users/me", headers=author, json={"hall": {"tabs": []}}).status_code == 422
    # someone else's picture can't be a banner
    assert client.patch("/api/users/me", headers=reader, json={"hall": {"cover_url": banner["url"]}}).status_code == 422


# ---------------------------------------------------------------- the last comments in the feed (cached)

def test_feed_shows_the_last_comments_and_forgets_them_on_change(author, reader):
    post = _post(author, content_md="Что вы слушаете этой осенью?")

    def preview():
        item = next(i for i in client.get("/api/feed").json()["items"] if i.get("post") and i["post"]["id"] == post["id"])
        return [c["content_md"] for c in item["comments"]]

    assert preview() == []  # now cached as «no comments»
    ids = []
    for text in ("Малер", "Шнитке", "Пярт"):
        r = client.post("/api/comments", headers=reader, json={"post_id": post["id"], "content_md": text})
        ids.append(r.json()["id"])
        assert preview()[-1] == text  # a new comment clears the cached thread at once
    assert preview() == ["Шнитке", "Пярт"]  # the last two, oldest first
    client.delete(f"/api/comments/{ids[-1]}", headers=reader)
    assert preview() == ["Малер", "Шнитке"]


def test_memory_cache_expires_and_stays_bounded():
    import time

    from allegro.core.cache import MemoryCache
    c = MemoryCache(max_keys=3)
    c.set_many({"a": [1], "b": {"x": "ё"}}, ttl=60)
    assert c.get_many(["a", "b", "z"]) == {"a": [1], "b": {"x": "ё"}}
    c.set_many({"gone": 1}, ttl=0)
    time.sleep(0.01)
    assert c.get_many(["gone"]) == {}
    c.set_many({"c": 1, "d": 2, "e": 3}, ttl=60)  # over the limit: starts afresh
    assert len(c.get_many(["a", "b", "c", "d", "e"])) <= 3



# ---------------------------------------------------------------- sketches

def test_sketches_are_quick_recordings_that_may_ask_for_feedback(author, composer, reader):
    voice = upload(composer, "voice.webm", b"\x1aE\xdf\xa3 webm", "audio/webm", "audio")
    assert voice["content_type"] == "audio/webm"  # a browser recording is audio, not video
    note = {"url": voice["url"], "name": "voice.webm", "content_type": voice["content_type"], "size": 9}
    body = {"kind": "sketch", "title": "Импровизация в ре миноре", "attachments": [note], "seeking_feedback": True}

    # composers only; one recording; a short title
    assert client.post("/api/posts", headers=author, json=body).status_code == 403  # a theorist
    assert client.post("/api/posts", headers=composer, json={**body, "attachments": []}).status_code == 422
    assert client.post("/api/posts", headers=composer, json={**body, "title": "x" * 121}).status_code == 422
    r = client.post("/api/posts", headers=composer, json=body)
    assert r.status_code == 201 and r.json()["seeking_feedback"] is True
    sketch = r.json()

    def feed(kind):
        return [i["post"]["id"] for i in client.get("/api/feed", params={"kind": kind}).json()["items"] if i.get("post")]

    assert sketch["id"] in feed("sketches") and sketch["id"] in feed("feedback") and sketch["id"] in feed("all")
    # enough feedback: the author takes the flag off
    client.patch(f"/api/posts/{sketch['slug']}", headers=composer, json={"seeking_feedback": False})
    assert sketch["id"] not in feed("feedback") and sketch["id"] in feed("sketches")
    # the flag belongs to sketches only
    note_post = client.post("/api/posts", headers=reader, json={"kind": "note", "content_md": "x", "seeking_feedback": True}).json()
    assert note_post["seeking_feedback"] is False
