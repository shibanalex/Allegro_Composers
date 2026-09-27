"""Generators for demo media: painterly SVG artwork, engraved-looking PDF scores, synthesized recordings and MusicXML.

Only used by scripts/seed.py — lets the design be tested with real page turns and timecodes.
"""
import io
import math
import random
import wave
from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------- painterly SVG

# Old-master palettes: (ground, deep shadow, light, mid tone, accent)
PALETTES = [
    ("#120c07", "#050302", "#e0a959", "#6b4020", "#8c2a1c"),  # candlelight umber
    ("#0b0f0e", "#030504", "#a8b89a", "#2f4a42", "#6d5a2e"),  # moonlit green
    ("#130809", "#050203", "#d98c6a", "#5a1c20", "#b0803e"),  # oxblood & rose
    ("#0f0b08", "#040302", "#f0d08a", "#4d3a22", "#3a4a5a"),  # golden hour
    ("#07090f", "#020305", "#9fb4d8", "#26324d", "#8a6a3a"),  # nocturne blue
]


def painting_svg(title: str, palette: int, seed: int, w: int = 1200, h: int = 800, portrait: bool = False) -> bytes:
    """Chiaroscuro 'oil painting' with brush-stroke displacement, varnish and vignette.
    portrait=True paints a dark head-and-shoulders silhouette against the light."""
    ground, shadow, light, mid, accent = PALETTES[palette % len(PALETTES)]
    lx, ly = (0.28 + (seed % 5) * 0.1) * w, (0.28 + (seed % 3) * 0.08) * h
    figure = ""
    if portrait:
        cx = w / 2
        figure = f"""
  <g filter="url(#paint2)" fill="{shadow}">
    <ellipse cx="{cx}" cy="{h * .42}" rx="{w * .17}" ry="{h * .2}" fill="{mid}" opacity=".9"/>
    <ellipse cx="{cx}" cy="{h * .43}" rx="{w * .12}" ry="{h * .15}"/>
    <path d="M{w * .12} {h} C{w * .18} {h * .72} {w * .35} {h * .64} {cx} {h * .64} S{w * .82} {h * .72} {w * .88} {h} Z"/>
  </g>"""
    caption = "" if portrait else (
        f'<text x="50%" y="{h * .86}" text-anchor="middle" font-family="Georgia, serif" font-size="{w // 26}" '
        f'fill="#f0dcae" fill-opacity=".7" font-style="italic">{title}</text>'
    )
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <filter id="paint" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.006 0.022" numOctaves="4" seed="{seed}" result="t"/>
      <feGaussianBlur in="SourceGraphic" stdDeviation="30" result="b"/>
      <feDisplacementMap in="b" in2="t" scale="160" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="paint2" x="-20%" y="-20%" width="140%" height="140%">
      <feTurbulence type="fractalNoise" baseFrequency="0.02 0.05" numOctaves="3" seed="{seed + 1}" result="t"/>
      <feGaussianBlur in="SourceGraphic" stdDeviation="6" result="b"/>
      <feDisplacementMap in="b" in2="t" scale="40" xChannelSelector="R" yChannelSelector="G"/>
    </filter>
    <filter id="strokes">
      <feTurbulence type="fractalNoise" baseFrequency="0.002 0.06" numOctaves="3" seed="{seed + 3}"/>
      <feColorMatrix values="0 0 0 0 1  0 0 0 0 .9  0 0 0 0 .75  0 0 0 1.2 -.55"/>
    </filter>
    <filter id="grain">
      <feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="{seed}"/>
      <feColorMatrix values="0 0 0 0 .5  0 0 0 0 .45  0 0 0 0 .35  0 0 0 .18 0"/>
    </filter>
    <radialGradient id="glow" cx="{lx / w:.2f}" cy="{ly / h:.2f}" r=".55">
      <stop offset="0" stop-color="{light}" stop-opacity=".85"/>
      <stop offset=".35" stop-color="{mid}" stop-opacity=".55"/>
      <stop offset="1" stop-color="{shadow}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="vignette" cx=".5" cy=".5" r=".75">
      <stop offset=".45" stop-color="#000" stop-opacity="0"/>
      <stop offset="1" stop-color="#000" stop-opacity=".85"/>
    </radialGradient>
    <linearGradient id="varnish" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#c8902c" stop-opacity=".10"/>
      <stop offset="1" stop-color="#3a1a05" stop-opacity=".25"/>
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="{ground}"/>
  <rect width="100%" height="100%" fill="url(#glow)"/>
  <g filter="url(#paint)">
    <ellipse cx="{lx}" cy="{ly}" rx="{w * .22}" ry="{h * .2}" fill="{light}" opacity=".55"/>
    <ellipse cx="{w * .75}" cy="{h * .7}" rx="{w * .3}" ry="{h * .25}" fill="{mid}" opacity=".8"/>
    <ellipse cx="{w * .15}" cy="{h * .85}" rx="{w * .25}" ry="{h * .18}" fill="{accent}" opacity=".45"/>
    <ellipse cx="{w * .85}" cy="{h * .15}" rx="{w * .2}" ry="{h * .15}" fill="{shadow}" opacity=".9"/>
  </g>{figure}
  <rect width="100%" height="100%" filter="url(#strokes)" opacity=".22" style="mix-blend-mode:soft-light"/>
  <rect width="100%" height="100%" filter="url(#grain)"/>
  <rect width="100%" height="100%" fill="url(#varnish)"/>
  <rect width="100%" height="100%" fill="url(#vignette)"/>
  {caption}
</svg>"""
    return svg.encode("utf-8")


# ---------------------------------------------------------------- PDF score

def _pdf_text(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _notehead(x: float, y: float, filled: bool) -> str:
    """Tilted oval notehead drawn with Bezier curves"""
    rx, ry, k = 3.6, 2.5, 0.5523
    path = (
        f"{rx} 0 m {rx} {ry * k} {rx * k} {ry} 0 {ry} c {-rx * k} {ry} {-rx} {ry * k} {-rx} 0 c "
        f"{-rx} {-ry * k} {-rx * k} {-ry} 0 {-ry} c {rx * k} {-ry} {rx} {-ry * k} {rx} 0 c"
    )
    c, s = math.cos(math.radians(20)), math.sin(math.radians(20))
    return f"q {c:.3f} {s:.3f} {-s:.3f} {c:.3f} {x:.1f} {y:.1f} cm {path} {'f' if filled else 'S'} Q\n"


def score_pdf(title: str, movement: str, tempo: str, instruments: list[str], pages: int, seed: int) -> bytes:
    """Multi-page A4 score with staves, bar lines, notes and page numbers (text must be Latin-1)"""
    rng = random.Random(seed)
    W, H = 595, 842
    staff_gap = 7.0
    staves = len(instruments)
    system_height = staves * 4 * staff_gap + (staves - 1) * 26
    streams = []

    for page in range(1, pages + 1):
        ops = ["0.97 0.95 0.9 rg 0 0 %d %d re f\n" % (W, H), "0.12 0.1 0.08 RG 0.12 0.1 0.08 rg\n"]
        top = H - 70
        if page == 1:
            ops.append(f"BT /F3 22 Tf {W / 2 - len(title) * 5.4:.0f} {H - 70} Td ({_pdf_text(title)}) Tj ET\n")
            ops.append(f"BT /F1 13 Tf {W / 2 - len(movement) * 3:.0f} {H - 92} Td ({_pdf_text(movement)}) Tj ET\n")
            top = H - 140
        else:
            ops.append(f"BT /F1 9 Tf 60 {H - 40} Td ({_pdf_text(title + ' - ' + movement)}) Tj ET\n")
        systems = max(1, int((top - 70) // (system_height + 48)))
        left, right = 78, W - 50
        for sys_i in range(systems):
            y0 = top - sys_i * (system_height + 48)
            if page == 1 and sys_i == 0:
                ops.append(f"BT /F2 12 Tf {left} {y0 + 14} Td ({_pdf_text(tempo)}) Tj ET\n")
            bar_no = (page - 1) * systems * 4 + sys_i * 4 + 1
            ops.append(f"BT /F1 7 Tf {left - 4} {y0 + 5} Td ({bar_no}) Tj ET\n")
            staff_tops = [y0 - i * (4 * staff_gap + 26) for i in range(staves)]
            ops.append("0.6 w\n")
            for i, st in enumerate(staff_tops):
                ops.append(f"BT /F2 8 Tf 28 {st - 2 * staff_gap - 3:.1f} Td ({_pdf_text(instruments[i])}) Tj ET\n")
                for line in range(5):
                    y = st - line * staff_gap
                    ops.append(f"{left} {y:.1f} m {right} {y:.1f} l S\n")
            # System bracket and bar lines through all staves
            bottom = staff_tops[-1] - 4 * staff_gap
            ops.append(f"2 w {left - 5} {y0:.1f} m {left - 5} {bottom:.1f} l S 0.8 w\n")
            bar_w = (right - left - 20) / 4
            for b in range(5):
                x = left + 20 + b * bar_w if b else left
                ops.append(f"{x:.1f} {y0:.1f} m {x:.1f} {bottom:.1f} l S\n")
            ops.append("0.7 w\n")
            for st in staff_tops:
                for b in range(4):
                    beats = rng.choice([2, 3, 4, 4, 6, 8])
                    for n in range(beats):
                        x = left + 26 + b * bar_w + (n + 0.5) * (bar_w - 12) / beats
                        step = rng.randint(-2, 10)
                        y = st - 4 * staff_gap + step * staff_gap / 2
                        filled = beats > 2
                        ops.append(_notehead(x, y, filled))
                        # Ledger lines outside the staff
                        for ly in (st + staff_gap, st - 5 * staff_gap):
                            if (ly > st and y >= ly - 1) or (ly < st and y <= ly + 1):
                                ops.append(f"{x - 6:.1f} {ly:.1f} m {x + 6:.1f} {ly:.1f} l S\n")
                        up = step < 4
                        sx = x + (3.3 if up else -3.3)
                        ops.append(f"{sx:.1f} {y:.1f} m {sx:.1f} {y + (24 if up else -24):.1f} l S\n")
        ops.append(f"BT /F1 9 Tf {W / 2 - 4} 30 Td ({page}) Tj ET\n")
        streams.append("".join(ops).encode("latin-1"))

    # Assemble objects: 1 catalog, 2 pages, 3-5 fonts, then page + content pairs
    objects = {
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Roman /Encoding /WinAnsiEncoding >>",
        4: b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Italic /Encoding /WinAnsiEncoding >>",
        5: b"<< /Type /Font /Subtype /Type1 /BaseFont /Times-Bold /Encoding /WinAnsiEncoding >>",
    }
    kids = []
    for i, stream in enumerate(streams):
        page_id, content_id = 6 + i * 2, 7 + i * 2
        kids.append(f"{page_id} 0 R")
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Contents {content_id} 0 R "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R >> >> >>"
        ).encode()
        objects[content_id] = b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[2] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(kids)} >>".encode()

    out = io.BytesIO()
    out.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for obj_id in sorted(objects):
        offsets[obj_id] = out.tell()
        out.write(b"%d 0 obj\n" % obj_id + objects[obj_id] + b"\nendobj\n")
    xref = out.tell()
    count = max(objects) + 1
    out.write(b"xref\n0 %d\n0000000000 65535 f \n" % count)
    for obj_id in range(1, count):
        out.write(b"%010d 00000 n \n" % offsets[obj_id])
    out.write(b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (count, xref))
    return out.getvalue()


# ---------------------------------------------------------------- audio

SR = 22050
NOTE = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
MINOR = [0, 2, 3, 5, 7, 8, 10]
MAJOR = [0, 2, 4, 5, 7, 9, 11]


def _freq(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def _tone(midi: int, seconds: float, timbre: str, velocity: float) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    f = _freq(midi)
    if timbre == "strings":
        wave_ = sum(np.sin(2 * np.pi * f * k * t * (1 + 0.002 * np.sin(2 * np.pi * 5.5 * t))) / k ** 1.3 for k in range(1, 7))
        env = np.minimum(t / 0.12, 1) * np.minimum((seconds - t) / 0.15, 1).clip(0, 1)
    elif timbre == "choir":
        wave_ = sum(np.sin(2 * np.pi * f * k * t + 0.3 * np.sin(2 * np.pi * 4.8 * t)) * a for k, a in ((1, 1), (2, .5), (3, .35), (4, .1)))
        env = np.minimum(t / 0.25, 1) * np.minimum((seconds - t) / 0.3, 1).clip(0, 1)
    elif timbre == "horn":
        wave_ = sum(np.sin(2 * np.pi * f * k * t) / k ** 1.8 for k in range(1, 6))
        env = np.minimum(t / 0.08, 1) * np.minimum((seconds - t) / 0.2, 1).clip(0, 1)
    else:  # piano
        wave_ = sum(np.sin(2 * np.pi * f * k * t) * np.exp(-t * (1.6 + 1.3 * k)) / k ** 1.1 for k in range(1, 7))
        env = np.minimum(t / 0.004, 1) * np.exp(-t * 0.9) * np.minimum((seconds - t) / 0.05, 1).clip(0, 1)
    return (wave_ * env * velocity).astype(np.float32)


@dataclass
class Note:
    midi: int
    start: float  # beats from the beginning
    length: float  # beats
    role: str  # melody | accomp | bass | pad
    timbre: str
    velocity: float


@dataclass
class Piece:
    """A composed piece: the same notes are rendered to audio and engraved as MusicXML, so they match exactly"""
    key: str
    minor: bool
    bpm: int
    bars: int
    notes: list[Note] = field(default_factory=list)

    @property
    def beat_seconds(self) -> float:
        return 60 / self.bpm


def compose(key: str, minor: bool, bpm: int, progression: list[int], bars: int, layers: list[str], seed: int) -> Piece:
    """Broken-chord accompaniment + a wandering melody (+ sustained voices) in 4/4"""
    rng = random.Random(seed)
    scale = MINOR if minor else MAJOR
    root = 48 + NOTE[key]
    piece = Piece(key, minor, bpm, bars)

    def degree(d, octave=0):
        return root + 12 * (octave + d // 7) + scale[d % 7]

    lead = "strings" if "violin" in layers else ("choir" if "choir" in layers else "piano")
    bass_timbre = "strings" if "strings" in layers else "piano"
    melody_deg = 9
    for bar in range(bars):
        chord = progression[bar % len(progression)]
        chord_tones = [chord, chord + 2, chord + 4]
        b0 = bar * 4
        piece.notes.append(Note(degree(chord, -1), b0, 4, "bass", bass_timbre, 0.35 if bass_timbre == "strings" else 0.5))
        for e in range(8):
            piece.notes.append(Note(degree(chord_tones[[0, 1, 2, 1][e % 4]], 0), b0 + e / 2, 0.5, "accomp", "piano", 0.22))
        for layer in layers:
            if layer in ("choir", "horn", "strings"):
                piece.notes.append(Note(degree(chord_tones[1], 1 if layer == "choir" else 0), b0, 4, "pad", layer, 0.18))
        # Melody: random walk leaning on chord tones, phrase ending every 4 bars
        pos = 0.0
        while pos < 4:
            length = 4 - pos if bar % 4 == 3 and pos >= 2 else rng.choice([0.5, 1, 1, 1.5, 2])
            length = min(length, 4 - pos)
            melody_deg += rng.choice([-2, -1, -1, 1, 1, 2])
            if rng.random() < 0.35:
                melody_deg = min(chord_tones, key=lambda c: abs((c + 7) - melody_deg)) + 7
            melody_deg = max(7, min(14, melody_deg))
            piece.notes.append(Note(degree(melody_deg, 0), b0 + pos, length, "melody", lead, 0.42))
            pos += length
    return piece


def render_wav(piece: Piece) -> tuple[bytes, float]:
    """Synthesize the piece; beat 1 of bar 1 sounds at 0.0 s. Returns WAV bytes and duration in seconds."""
    beat = piece.beat_seconds
    total = piece.bars * 4 * beat + 3.0
    buf = np.zeros(int(total * SR) + SR, dtype=np.float32)
    for n in piece.notes:
        # Melody and accompaniment ring slightly longer than written (legato / pedal)
        ring = {"melody": 1.1, "accomp": 2.8}.get(n.role, 1.0)
        tone = _tone(n.midi, n.length * beat * ring, n.timbre, n.velocity)
        i = int(n.start * beat * SR)
        buf[i:i + len(tone)] += tone[: len(buf) - i]

    # Simple hall: a few decaying echoes
    wet = np.zeros_like(buf)
    for delay, gain in ((0.031, .35), (0.047, .3), (0.083, .22), (0.127, .15), (0.211, .1)):
        d = int(delay * SR)
        wet[d:] += buf[:-d] * gain
    mix = buf + wet
    mix /= max(1e-6, np.abs(mix).max()) / 0.85
    fade = int(2.0 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    pcm = (mix * 32767).astype("<i2")

    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return out.getvalue(), round(len(pcm) / SR, 2)


# ---------------------------------------------------------------- MusicXML

_SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
_MAJOR_FIFTHS = {0: 0, 7: 1, 2: 2, 9: 3, 4: 4, 11: 5, 6: 6, 5: -1, 10: -2, 3: -3, 8: -4, 1: -5}
# divisions = 2 per quarter → an eighth lasts 1
_TYPES = {1: ("eighth", False), 2: ("quarter", False), 3: ("quarter", True), 4: ("half", False), 6: ("half", True), 8: ("whole", False)}


def _fifths(piece: Piece) -> int:
    tonic = NOTE[piece.key]
    return _MAJOR_FIFTHS[(tonic + 3) % 12 if piece.minor else tonic]


def _pitch_xml(midi: int, flats: bool) -> str:
    name = (_FLATS if flats else _SHARPS)[midi % 12]
    alter = {"#": 1, "b": -1}.get(name[1:], 0)
    octave = midi // 12 - 1
    return f"<pitch><step>{name[0]}</step>{f'<alter>{alter}</alter>' if alter else ''}<octave>{octave}</octave></pitch>"


def _note_xml(midi: int, beats: float, flats: bool, beam: str = "") -> str:
    duration = int(round(beats * 2))
    kind, dotted = _TYPES[duration]
    return (
        f"<note>{_pitch_xml(midi, flats)}<duration>{duration}</duration><voice>1</voice><type>{kind}</type>"
        f"{'<dot/>' if dotted else ''}{f'<beam number=\"1\">{beam}</beam>' if beam else ''}</note>"
    )


def piece_musicxml(piece: Piece, title: str, composer: str, tempo_word: str, parts: tuple[str, str]) -> bytes:
    """Engrave melody (treble clef) and accompaniment (bass clef) of the piece as MusicXML 4.0"""
    fifths = _fifths(piece)
    flats = fifths < 0
    melody = sorted((n for n in piece.notes if n.role == "melody"), key=lambda n: n.start)
    accomp = sorted((n for n in piece.notes if n.role == "accomp"), key=lambda n: n.start)

    def part(part_id: str, notes: list[Note], clef: tuple[str, int], beamed: bool) -> str:
        measures = []
        for bar in range(piece.bars):
            body = []
            if bar == 0:
                body.append(
                    f"<attributes><divisions>2</divisions><key><fifths>{fifths}</fifths>"
                    f"<mode>{'minor' if piece.minor else 'major'}</mode></key>"
                    f"<time><beats>4</beats><beat-type>4</beat-type></time>"
                    f"<clef><sign>{clef[0]}</sign><line>{clef[1]}</line></clef></attributes>"
                )
                if part_id == "P1":
                    body.append(
                        f'<direction placement="above"><direction-type><words font-style="italic" font-weight="bold">{tempo_word}</words></direction-type></direction>'
                        f'<direction placement="above"><direction-type><metronome><beat-unit>quarter</beat-unit>'
                        f'<per-minute>{piece.bpm}</per-minute></metronome></direction-type><sound tempo="{piece.bpm}"/></direction>'
                    )
            in_bar = [n for n in notes if bar * 4 <= n.start < bar * 4 + 4]
            for i, n in enumerate(in_bar):
                beam = ""
                if beamed:
                    beam = ("begin", "continue", "continue", "end")[i % 4]
                body.append(_note_xml(n.midi, n.length, flats, beam))
            if bar == piece.bars - 1:
                body.append('<barline location="right"><bar-style>light-heavy</bar-style></barline>')
            measures.append(f'<measure number="{bar + 1}">{"".join(body)}</measure>')
        return f'<part id="{part_id}">{"".join(measures)}</part>'

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">'
        '<score-partwise version="4.0">'
        f"<work><work-title>{title}</work-title></work>"
        f'<identification><creator type="composer">{composer}</creator></identification>'
        "<part-list>"
        f'<score-part id="P1"><part-name>{parts[0]}</part-name></score-part>'
        f'<score-part id="P2"><part-name>{parts[1]}</part-name></score-part>'
        "</part-list>"
        + part("P1", melody, ("G", 2), beamed=False)
        + part("P2", accomp, ("F", 4), beamed=True)
        + "</score-partwise>"
    )
    return xml.encode("utf-8")
