"""Nobody can change or delete what belongs to someone else — checked for every endpoint at once.

The list of endpoints comes from the application itself (its OpenAPI schema), so a new endpoint is checked
the day it appears. Member B calls every changing endpoint with the ids of member A's things; anything
but a refusal fails the test, and A's things must be as they were.
"""
import re

import pytest

from tests.support import PDF, client, create_opus, register, set_user, upload

MEMBERS = ["iso_owner", "iso_player", "iso_intruder"]
# What a stranger may do to someone else's thing, by design
ALLOWED = {
    ("put", "/api/reactions/{kind}/{target_id}"),  # like it
    ("delete", "/api/reactions/{kind}/{target_id}"),  # take one's own like back
    ("post", "/api/opuses/{slug}/play"),  # a play is counted
    ("post", "/api/performances/{performance_id}/play"),
}
REFUSED = {401, 403, 404, 405, 409, 422}


@pytest.fixture(scope="module", autouse=True)
def _leave_no_trace():
    yield
    for username in MEMBERS:
        set_user(username, is_hidden=True)


@pytest.fixture(scope="module")
def things():
    """Member A's things of every kind, and the ids a stranger would try"""
    owner = register("iso_owner", "Владелец", role="composer")
    player = register("iso_player", "Исполнитель", role="performer")
    score = upload(owner, "iso.pdf", PDF, "application/pdf", "score")
    opus = create_opus(owner, title="Чужая соната", score_file_key=score["key"], score_page_count=1)
    post = client.post("/api/posts", headers=owner, json={"kind": "note", "content_md": "Моё"}).json()
    collection = client.post("/api/collections", headers=owner, json={"title": "Мой цикл", "opus_ids": [opus["id"]]}).json()
    material = client.post("/api/materials", headers=owner, json={"kind": "book", "title": "Моя книга"}).json()
    comment = client.post("/api/comments", headers=owner, json={"post_id": post["id"], "content_md": "Мой комментарий"}).json()
    feedback = client.post("/api/feedback", headers=owner, json={"kind": "idea", "title": "Моё предложение", "body": "Текст"}).json()
    performance = client.post("/api/performances", headers=player, json={
        "opus_id": opus["id"], "audio_type": "youtube", "audio_source": "https://youtu.be/dQw4w9WgXcQ",
    }).json()
    owner_id = client.get("/api/auth/me", headers=owner).json()["id"]
    ids = {
        "slug": [opus["slug"], post["slug"], "about"], "collection_id": [collection["id"]], "material_id": [material["id"]],
        "comment_id": [comment["id"]], "feedback_id": [feedback["id"]], "performance_id": [performance["id"]],
        "user_id": [owner_id], "link_id": [owner_id], "kind": ["post"], "target_id": [post["id"]],
    }
    return {"owner": owner, "opus": opus, "post": post, "collection": collection, "material": material,
            "comment": comment, "feedback": feedback, "performance": performance, "ids": ids}


def _paths_with_ids():
    from allegro.main import app
    for path, ops in app.openapi()["paths"].items():
        if "{" not in path:
            continue  # without an id in the address an endpoint acts on the caller's own account
        for method in ops:
            if method in ("post", "put", "patch", "delete") and (method, path) not in ALLOWED:
                yield method, path


def _fill(path: str, ids: dict) -> list[str]:
    """Every way to fill the address with the owner's ids"""
    paths = [path]
    for name in re.findall(r"{(\w+)}", path):
        paths = [p.replace("{" + name + "}", str(value)) for p in paths for value in ids[name]]
    return paths


BODIES = {  # a plausible body, so a refusal comes from the rights and not from a malformed request
    "patch": {"title": "Взлом", "content_md": "Взлом", "status": "draft", "is_admin": True, "reply_md": "x", "description": "x"},
    "put": {"content_md": "Взлом", "title": "Взлом", "markers": [], "body_md": "Взлом"},
    "post": {"note": "x"},
    "delete": None,
}


def test_a_stranger_can_change_nothing_of_someone_elses(things):
    intruder = register("iso_intruder", "Чужой", role="composer")
    tried = 0
    for method, path in _paths_with_ids():
        for url in _fill(path, things["ids"]):
            body = BODIES[method]
            r = client.request(method.upper(), url, headers=intruder, json=body) if body is not None else client.request(method.upper(), url, headers=intruder)
            tried += 1
            assert r.status_code in REFUSED, f"{method.upper()} {url} → {r.status_code} {r.text[:200]}"
    assert tried >= 20
    # the control: the owner may do the same with the same bodies — the refusals above were about rights
    owner = things["owner"]
    assert client.patch(f"/api/collections/{things['collection']['id']}", headers=owner, json=BODIES["patch"]).status_code == 200
    assert client.patch(f"/api/materials/{things['material']['id']}", headers=owner, json=BODIES["patch"]).status_code == 200
    client.patch(f"/api/collections/{things['collection']['id']}", headers=owner, json={"title": "Мой цикл"})
    client.patch(f"/api/materials/{things['material']['id']}", headers=owner, json={"title": "Моя книга"})

    # and everything of the owner's is as it was
    owner = things["owner"]
    assert client.get(f"/api/opuses/{things['opus']['slug']}").json()["title"] == "Чужая соната"
    assert client.get(f"/api/opuses/{things['opus']['slug']}").json()["score_file_key"] == things["opus"]["score_file_key"]
    assert client.get(f"/api/posts/{things['post']['slug']}").json()["content_md"] == "Моё"
    assert [c["id"] for c in client.get("/api/comments", params={"post_id": things["post"]["id"]}).json()] == [things["comment"]["id"]]
    collections = client.get("/api/collections", params={"author": "iso_owner"}).json()
    assert collections[0]["title"] == "Мой цикл"
    assert client.get("/api/materials", params={"author": "iso_owner"}).json()[0]["title"] == "Моя книга"
    assert client.get("/api/performances", params={"opus": things["opus"]["slug"]}).json()["total"] == 1
    assert client.get("/api/auth/me", headers=owner).json()["is_admin"] is False


def test_without_signing_in_nothing_changes(things):
    for method, path in _paths_with_ids():
        for url in _fill(path, things["ids"]):
            r = client.request(method.upper(), url, json=BODIES[method]) if BODIES[method] is not None else client.request(method.upper(), url)
            assert r.status_code in REFUSED, f"anonymous {method.upper()} {url} → {r.status_code}"
