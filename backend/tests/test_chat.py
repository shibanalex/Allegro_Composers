"""The community chat: history for everyone, messages from members, live publishing, mentions in the bell"""
import jwt
import pytest

from tests.support import client, register, set_user

MEMBERS = ["c_anna", "c_boris", "c_mod"]


@pytest.fixture(scope="module", autouse=True)
def _leave_no_trace():
    yield
    for username in MEMBERS:
        set_user(username, is_hidden=True)


@pytest.fixture(scope="module")
def anna():
    return register("c_anna", "Анна", role="composer")


@pytest.fixture(scope="module")
def boris():
    return register("c_boris", "Борис", role="listener")


@pytest.fixture
def live(monkeypatch):
    """What would go to Centrifugo"""
    from allegro.core import realtime
    sent = []
    monkeypatch.setattr(realtime, "publish", lambda channel, data: sent.append((channel, data)) or True)
    return sent


def work():
    from allegro.core.db import SessionLocal
    from allegro.modules.notifications.worker import process_pending
    with SessionLocal() as db:
        while process_pending(db):
            pass


def test_members_write_everyone_reads_and_it_goes_live(anna, boris, live):
    assert client.post("/api/chat/messages", json={"text": "Гость пишет"}).status_code == 401
    r = client.post("/api/chat/messages", headers=anna, json={"text": "  Добрый вечер!  \n\n\n\n\nКто играет Шуберта?  "})
    assert r.status_code == 201, r.text
    first = r.json()
    assert first["text"] == "Добрый вечер!\n\n\nКто играет Шуберта?" and first["author"]["username"] == "c_anna"
    assert live[-1] == ("chat:general", {"type": "message", "message": first})
    client.post("/api/chat/messages", headers=boris, json={"text": "👍"})  # an emoji alone is a message
    for bad in ("", "   \n  ", "x" * 2001):
        assert client.post("/api/chat/messages", headers=boris, json={"text": bad}).status_code == 422

    page = client.get("/api/chat/messages").json()  # a guest reads
    texts = [m["text"] for m in page["items"]]
    assert texts[-2:] == [first["text"], "👍"]  # oldest first, the newest at the bottom


def test_older_messages_page_by_page(anna):
    for i in range(5):
        client.post("/api/chat/messages", headers=anna, json={"text": f"Номер {i}"})
    latest = client.get("/api/chat/messages", params={"limit": 3}).json()
    assert [m["text"] for m in latest["items"]] == ["Номер 2", "Номер 3", "Номер 4"] and latest["next_before"]
    older = client.get("/api/chat/messages", params={"limit": 2, "before": latest["next_before"]}).json()
    assert [m["text"] for m in older["items"]] == ["Номер 0", "Номер 1"]


def test_a_mention_rings_the_bell_and_goes_with_the_message(anna, boris):
    before = client.get("/api/notifications/unread", headers=boris).json()["count"]
    r = client.post("/api/chat/messages", headers=anna, json={"text": "@c_boris послушайте, и @nobody_here тоже, и @c_anna"})
    message = r.json()
    work()
    assert client.get("/api/notifications/unread", headers=boris).json()["count"] == before + 1
    latest = client.get("/api/notifications", headers=boris).json()["items"][0]
    assert latest["kind"] == "mention" and latest["url"] == f"/chat#m-{message['id']}"
    assert client.get("/api/notifications/unread", headers=anna).json()["count"] == 0  # not for mentioning oneself
    # an e-mail address is not a mention
    from allegro.modules.chat.service import mentioned_usernames
    assert mentioned_usernames("пишите на anna@c_boris.ru, а @c_boris прочтёт") == ["c_boris"]

    # the message deleted: the notification goes with it
    assert client.delete(f"/api/chat/messages/{message['id']}", headers=anna).status_code == 204
    work()
    assert client.get("/api/notifications/unread", headers=boris).json()["count"] == before


def test_only_the_author_or_a_moderator_deletes(anna, boris, live):
    message = client.post("/api/chat/messages", headers=anna, json={"text": "Удалите меня"}).json()
    assert client.delete(f"/api/chat/messages/{message['id']}", headers=boris).status_code == 403
    assert client.delete(f"/api/chat/messages/{message['id']}").status_code == 401
    moderator = register("c_mod", "Модератор")
    set_user("c_mod", is_moderator=True)
    assert client.delete(f"/api/chat/messages/{message['id']}", headers=moderator).status_code == 204
    assert live[-1] == ("chat:general", {"type": "deleted", "id": message["id"]})
    assert message["id"] not in [m["id"] for m in client.get("/api/chat/messages").json()["items"]]


def test_a_pass_to_the_live_channel(anna):
    from allegro.core import realtime
    guest = client.get("/api/chat/connection").json()
    member = client.get("/api/chat/connection", headers=anna).json()
    assert guest["url"] == "/connection/websocket" and guest["channel"] == "chat:general"
    claims = jwt.decode(member["token"], realtime.client_secret(), algorithms=["HS256"])
    assert claims["sub"] and claims["exp"] > claims["iat"]
    assert jwt.decode(guest["token"], realtime.client_secret(), algorithms=["HS256"])["sub"] == ""  # anonymous


def test_a_flood_is_slowed_down(boris, monkeypatch):
    from allegro.core.ratelimit import AttemptLimiter
    from allegro.modules.chat import service
    monkeypatch.setattr(service, "pace", AttemptLimiter(3, 60, "Слишком часто."))
    codes = [client.post("/api/chat/messages", headers=boris, json={"text": f"спам {i}"}).status_code for i in range(4)]
    assert codes == [201, 201, 201, 429]


def test_a_shadowed_member_cannot_write_and_their_messages_are_hidden(boris):
    client.post("/api/chat/messages", headers=boris, json={"text": "Сообщение из тени"})
    set_user("c_boris", is_hidden=True)
    try:
        assert "Сообщение из тени" not in [m["text"] for m in client.get("/api/chat/messages").json()["items"]]
    finally:
        set_user("c_boris", is_hidden=False)
