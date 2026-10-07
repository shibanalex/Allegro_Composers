"""Waveforms of uploaded recordings (core.peaks) and comments on a stretch of the recording"""
import io
import math
import struct
import wave

import pytest

from tests.support import client, create_opus, register, set_user, upload

MEMBERS = ["w_author", "w_listener"]


@pytest.fixture(scope="module", autouse=True)
def _leave_no_trace():
    yield
    for username in MEMBERS:
        set_user(username, is_hidden=True)


@pytest.fixture(scope="module")
def author():
    return register("w_author", "Автор волны", role="composer")


@pytest.fixture(scope="module")
def listener():
    return register("w_listener", "Слушатель волны", role="listener")


def recording() -> bytes:
    """Three seconds: silence, a loud tone, a quiet tone"""
    rate = 8000
    samples = []
    for second, volume in enumerate((0.0, 0.9, 0.2)):
        samples += [int(volume * 32767 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(rate)]
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return out.getvalue()


def test_a_recording_gets_its_waveform(author):
    from allegro.core import peaks
    from allegro.core.storage import storage

    item = upload(author, "nocturne.wav", recording(), "audio/wav", "audio")
    r = client.get("/api/media/peaks", params={"url": item["url"]})  # drawn right after the upload
    assert r.status_code == 200, r.text
    data = r.json()
    assert 2.9 <= data["duration"] <= 3.1
    wave_ = data["peaks"]
    third = len(wave_) // 3
    silent, loud, quiet = (max(wave_[i * third + 2:(i + 1) * third - 2]) for i in range(3))
    assert silent < 0.01 and 0.8 < loud <= 1 and 0.1 < quiet < 0.3
    assert r.headers["cache-control"].startswith("public")

    # not a recording: no waveform, and a file that only pretends to be one is marked, not retried
    fake = upload(author, "broken.mp3", b"definitely not audio" * 50, "audio/mpeg", "audio")
    assert client.get("/api/media/peaks", params={"url": fake["url"]}).status_code == 404
    assert storage.exists(peaks.peaks_key(fake["key"]))
    assert client.get("/api/media/peaks", params={"url": "https://elsewhere.example/a.mp3"}).status_code == 404

    # the waveform goes away with its recording (as when an opus's audio is replaced or deleted)
    from allegro.core.db import SessionLocal
    from allegro.core.files import delete_own_after_commit
    with SessionLocal() as db:
        delete_own_after_commit(db, "w_author", item["key"])
        db.commit()
    assert not storage.exists(peaks.peaks_key(item["key"]))


def test_a_comment_on_a_stretch(author, listener):
    opus = create_opus(author, title="Ноктюрн с отрезками", audio_type="youtube", audio_source="https://youtu.be/dQw4w9WgXcQ")
    body = {"opus_id": opus["id"], "content_md": "Здесь модуляция"}
    r = client.post("/api/comments", headers=listener, json={**body, "timestamp_marker": 80, "timestamp_end": 105.5})
    assert r.status_code == 201, r.text
    assert (r.json()["timestamp_marker"], r.json()["timestamp_end"]) == (80, 105.5)
    listed = client.get("/api/comments", params={"opus_id": opus["id"]}).json()
    assert listed[0]["timestamp_end"] == 105.5
    # an end without a start, or one before it, is refused
    assert client.post("/api/comments", headers=listener, json={**body, "timestamp_end": 10}).status_code == 422
    assert client.post("/api/comments", headers=listener, json={**body, "timestamp_marker": 50, "timestamp_end": 40}).status_code == 422
    # a single moment still works
    assert client.post("/api/comments", headers=listener, json={**body, "timestamp_marker": 12}).json()["timestamp_end"] is None


def test_a_recording_marked_unreadable_by_an_older_version_is_tried_again(author):
    from allegro.core import peaks
    from allegro.core.storage import storage
    from scripts import make_peaks

    item = upload(author, "retry.wav", recording(), "audio/wav", "audio")
    storage.save_bytes(peaks.peaks_key(item["key"]), b'{"duration":null,"peaks":[],"error":true}')  # an old failure
    assert client.get("/api/media/peaks", params={"url": item["url"]}).status_code == 404
    make_peaks.main()
    assert len(client.get("/api/media/peaks", params={"url": item["url"]}).json()["peaks"]) > 10
    # a failure by this version stays put: the start of the server doesn't redo it every time
    fake = upload(author, "still-broken.mp3", b"nope" * 100, "audio/mpeg", "audio")
    assert not peaks.stale(fake["key"])
