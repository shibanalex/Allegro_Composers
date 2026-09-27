"""Minimal MusicXML reader: measure timeline and page breaks.

Used to turn PDF pages in sync with the recording automatically: MuseScore, Sibelius, Dorico and Finale
write their page layout into the export (<print new-page="yes">), so the MusicXML knows on which
measure every PDF page starts, and the written tempo tells when that measure sounds.
"""
import io
import zipfile
from dataclasses import dataclass
from typing import Optional
from xml.etree import ElementTree as ET


MAX_XML_BYTES = 64 * 1024 * 1024


@dataclass
class MeasureInfo:
    number: int  # ordinal, 1-based (MusicXML "number" attributes may repeat or be text)
    start_seconds: float  # at the written tempo, from the first beat
    new_page: bool


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def read_score_xml(data: bytes) -> bytes:
    """Plain .musicxml/.xml, or the root file of a compressed .mxl container"""
    if not data.startswith(b"PK"):
        return data
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root_path = None
        if "META-INF/container.xml" in z.namelist():
            container = ET.fromstring(z.read("META-INF/container.xml"))
            for el in container.iter():
                if _local(el.tag) == "rootfile" and el.get("full-path"):
                    root_path = el.get("full-path")
                    break
        if not root_path:
            root_path = next(n for n in z.namelist() if n.lower().endswith((".musicxml", ".xml")) and not n.startswith("META-INF"))
        # A tiny archive may unpack to gigabytes ("zip bomb"): real scores are a few MB of XML
        if z.getinfo(root_path).file_size > MAX_XML_BYTES:
            raise ValueError("MusicXML is too large")
        return z.read(root_path)


def measure_timeline(xml: bytes) -> list[MeasureInfo]:
    """Start time of every measure of the first part, following divisions, time signatures and tempo marks.
    Repeats are not unrolled (a recording that repeats sections needs measure markers)."""
    root = ET.fromstring(xml)
    part = next((el for el in root if _local(el.tag) == "part"), None)
    if part is None:
        return []

    divisions = 1.0
    beats, beat_type = 4, 4
    tempo = 120.0
    seconds = 0.0
    result: list[MeasureInfo] = []

    for index, measure in enumerate(el for el in part if _local(el.tag) == "measure"):
        new_page = any(_local(el.tag) == "print" and el.get("new-page") == "yes" for el in measure)
        start = seconds
        position = 0.0  # in divisions
        longest = 0.0
        measure_tempo = tempo
        tempo_changes: list[tuple[float, float]] = []  # (position, bpm) inside this measure

        for el in measure:
            tag = _local(el.tag)
            if tag == "attributes":
                for a in el:
                    if _local(a.tag) == "divisions" and a.text:
                        divisions = float(a.text)
                    elif _local(a.tag) == "time":
                        b = next((x.text for x in a if _local(x.tag) == "beats"), None)
                        t = next((x.text for x in a if _local(x.tag) == "beat-type"), None)
                        if b and t and b.isdigit() and t.isdigit():
                            beats, beat_type = int(b), int(t)
            elif tag in ("direction", "sound"):
                sound = el if tag == "sound" else next((x for x in el.iter() if _local(x.tag) == "sound"), None)
                if sound is not None and sound.get("tempo"):
                    try:
                        tempo_changes.append((position, float(sound.get("tempo"))))
                    except ValueError:
                        pass
            elif tag == "note":
                is_chord = any(_local(x.tag) == "chord" for x in el)
                is_grace = any(_local(x.tag) == "grace" for x in el)
                duration = next((float(x.text) for x in el if _local(x.tag) == "duration" and x.text), 0.0)
                if not is_chord and not is_grace:
                    position += duration
            elif tag == "backup":
                position -= next((float(x.text) for x in el if _local(x.tag) == "duration" and x.text), 0.0)
            elif tag == "forward":
                position += next((float(x.text) for x in el if _local(x.tag) == "duration" and x.text), 0.0)
            longest = max(longest, position)

        # A pickup measure is shorter than the time signature: use the notated length
        length = longest if longest > 0 else beats * (4 / beat_type) * divisions
        # Integrate tempo changes that happen inside the measure
        cursor = 0.0
        bpm = measure_tempo
        for pos, new_bpm in sorted(tempo_changes):
            pos = min(max(pos, 0.0), length)
            seconds += (pos - cursor) / divisions * 60 / bpm
            cursor, bpm = pos, new_bpm
        seconds += (length - cursor) / divisions * 60 / bpm
        tempo = bpm

        result.append(MeasureInfo(number=index + 1, start_seconds=start, new_page=new_page))
    return result


def to_recording_time(
    measures: list[MeasureInfo], offset: float, measure_markers: list[tuple[int, float]]
) -> dict[int, float]:
    """Recording second at which each measure starts: written tempo + offset, or piecewise-linear
    between the author's measure markers (same rule as the cursor in the browser)."""
    starts = {m.number: m.start_seconds for m in measures}
    anchors = sorted((starts[n], t) for n, t in measure_markers if n in starts)

    def map_time(s: float) -> float:
        if not anchors:
            return offset + s
        if s <= anchors[0][0]:
            return anchors[0][1] + (s - anchors[0][0])
        if s >= anchors[-1][0]:
            return anchors[-1][1] + (s - anchors[-1][0])
        for (s0, t0), (s1, t1) in zip(anchors, anchors[1:]):
            if s0 <= s <= s1:
                return t0 + (s - s0) / (s1 - s0) * (t1 - t0)
        return offset + s

    return {n: max(0.0, map_time(s)) for n, s in starts.items()}


def page_start_times(
    data: bytes, page_count: int, offset: float = 0.0, measure_markers: Optional[list[tuple[int, float]]] = None
) -> Optional[list[float]]:
    """Seconds at which each PDF page starts, if the MusicXML page layout matches the PDF page count"""
    measures = measure_timeline(read_score_xml(data))
    if not measures:
        return None
    page_first_measures = [measures[0].number] + [m.number for m in measures[1:] if m.new_page]
    if len(page_first_measures) != page_count:
        return None
    times = to_recording_time(measures, offset, measure_markers or [])
    return [round(times[n], 2) for n in page_first_measures]
