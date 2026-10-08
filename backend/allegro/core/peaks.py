"""The waveform of an uploaded recording: a light file of loudness peaks next to the audio.

A listener's browser can't draw a recording's waveform without downloading and decoding all of it
(megabytes, slow on a phone). So the server does it once: ffmpeg decodes the file as a stream into
mono at a low rate, and the loudest moment of each slice becomes one of POINTS numbers. They are
stored beside the original under `<key>.peaks.json`, the way pictures keep their previews (core.images),
so nothing is added to the database and the file lies in the same owner's folder (core.files).

ffmpeg comes from the imageio-ffmpeg package: one static binary, the same on the server and on a
developer's computer. It reads a copy on the server's own disk (storage.local_copy), never the network.
"""
import json
import logging
import subprocess
from array import array
from pathlib import PurePosixPath
from typing import Optional

from allegro.core.storage import storage

log = logging.getLogger("allegro.peaks")

PEAKS_SUFFIX = ".peaks.json"
VERSION = 2  # a recording marked unreadable by an older version is tried again
POINTS = 1200  # enough for the widest waveform on a screen; ~5 KB of JSON
RATE = 4000  # Hz: plenty to see the loudness, and decoding stays fast
SLICE = RATE // 20  # the loudest sample of every 1/20 s first, then those are gathered into POINTS
TIMEOUT = 300  # s: a recording that takes longer to decode is given up on
# Folders whose files may be recordings: uploads with purpose "audio" and attachments to posts
AUDIO_FOLDERS = ("audios/", "attachments/")
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".oga", ".opus", ".flac", ".m4a", ".aac", ".webm"}
DEMUXERS = "mp3,wav,ogg,flac,mov,aac,matroska"  # ffmpeg readers for those (mov: m4a; matroska: webm)


def is_audio(key: Optional[str]) -> bool:
    return (bool(key) and key.startswith(AUDIO_FOLDERS) and not key.endswith(PEAKS_SUFFIX)
            and ".." not in key.split("/") and "\\" not in key  # never a way out of the folder
            and PurePosixPath(key).suffix.lower() in AUDIO_EXTENSIONS)


def peaks_key(key: str) -> str:
    return key + PEAKS_SUFFIX


def _ffmpeg() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def compute(source: str) -> dict:
    """{"duration": seconds, "peaks": [0..1, ...]} of a file path or URL; raises ValueError if it isn't audio"""
    process = subprocess.Popen(
        [_ffmpeg(), "-nostdin", "-v", "error",
         # an upload is only ever read as an audio file on this disk: no playlists, scripts or network
         # (a file pretending to be audio must not make ffmpeg fetch addresses or read other files)
         "-protocol_whitelist", "file", "-format_whitelist", DEMUXERS,
         "-i", source, "-vn", "-ac", "1", "-ar", str(RATE), "-f", "s16le", "pipe:1"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    slices: list[int] = []
    samples = 0
    rest = b""
    try:
        while chunk := process.stdout.read(SLICE * 2 * 64):
            chunk = rest + chunk
            usable = len(chunk) - len(chunk) % (SLICE * 2)
            rest = chunk[usable:]
            pcm = array("h", chunk[:usable])
            samples += len(pcm)
            for i in range(0, len(pcm), SLICE):
                part = pcm[i:i + SLICE]
                slices.append(max(max(part), -min(part)))
        if rest:
            pcm = array("h", rest[: len(rest) - len(rest) % 2])
            if pcm:
                samples += len(pcm)
                slices.append(max(max(pcm), -min(pcm)))
        process.wait(timeout=TIMEOUT)
    finally:
        if process.poll() is None:
            process.kill()
    if process.returncode != 0 or not samples:
        error = process.stderr.read().decode(errors="replace").strip().splitlines()
        raise ValueError(error[-1] if error else "не удалось прочитать запись")
    # Gather the slices into POINTS (the loudest of each group), scaled to 0..1 of full scale
    step = max(1, -(-len(slices) // POINTS))
    peaks = [max(slices[i:i + step]) / 32768 for i in range(0, len(slices), step)]
    return {"duration": round(samples / RATE, 2), "peaks": [round(p, 3) for p in peaks]}


def make(key: str) -> bool:
    """Compute and store the waveform of one recording; False when it can't be read (a mark is stored, so it isn't retried)"""
    try:
        with storage.local_copy(key) as path:
            result = compute(str(path))
    except (ValueError, OSError, subprocess.TimeoutExpired) as e:
        log.warning("waveform of %s: %s", key, e)
        result = {"duration": None, "peaks": [], "error": True, "reason": str(e)[-200:]}
    result["v"] = VERSION
    storage.save_bytes(peaks_key(key), json.dumps(result, separators=(",", ":")).encode())
    return not result.get("error")


def make_quietly(key: str) -> None:
    """After an upload: a waveform that fails must not affect anything else"""
    try:
        make(key)
    except Exception:
        log.exception("waveform of %s", key)


def stale(key: str) -> bool:
    """No waveform yet, or only a mark of a failure by an older version"""
    if not storage.exists(peaks_key(key)):
        return True
    data = json.loads(storage.read_bytes(peaks_key(key)))
    return bool(data.get("error")) and data.get("v") != VERSION


def read(key: str) -> Optional[dict]:
    if not is_audio(key) or not storage.exists(peaks_key(key)):
        return None
    data = json.loads(storage.read_bytes(peaks_key(key)))
    return None if data.get("error") else data
