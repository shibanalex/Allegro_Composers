"""Search by words, the same way on SQLite (development) and PostgreSQL (production).

Russian words change their endings («полифония», «полифонии», «полифонию»), so every word is cut
to a rough stem before matching: good enough for a composer's blog without a full-text index.
Every word of the query must be found (in any of the searched columns); «ё» is treated as «е».
"""
import math
import re
from typing import Iterable

from sqlalchemy import and_, func, or_

MAX_WORDS = 6
_WORD = re.compile(r"[\wё]+", re.IGNORECASE)
_MARKDOWN = re.compile(r"!\[[^\]]*\]\([^)]*\)|\[([^\]]*)\]\([^)]*\)|[#>*_`~]")


def _fold(text: str) -> str:
    return text.lower().replace("ё", "е")


def stems(query: str) -> list[str]:
    """«Фортепьянное трио» → ["фортепьян", "трио"]: words shortened so any ending matches"""
    result = []
    for word in _WORD.findall(_fold(query))[:MAX_WORDS]:
        if len(word) > 4:
            word = word[: max(4, math.ceil(len(word) * 0.7))]
        if word not in result:
            result.append(word)
    return result


def _folded(column):
    return func.replace(func.lower(func.coalesce(column, "")), "ё", "е")


def matches_all(columns: Iterable, word_stems: list[str]):
    """SQL condition: every stem occurs in at least one of the columns"""
    columns = list(columns)
    return and_(*(or_(*(_folded(c).contains(s, autoescape=True) for c in columns)) for s in word_stems))


def plain(markdown: str) -> str:
    text = _MARKDOWN.sub(lambda m: m.group(1) or "", markdown or "")
    return re.sub(r"\s+", " ", text).strip()


def snippet(markdown: str, word_stems: list[str], before: int = 60, after: int = 140) -> str:
    """A piece of the text around the first found word, for the search results"""
    text = plain(markdown)
    folded = _fold(text)
    positions = [p for p in (folded.find(s) for s in word_stems) if p >= 0]
    if not positions:
        return text[: before + after] + ("…" if len(text) > before + after else "")
    start = max(0, min(positions) - before)
    end = min(len(text), min(positions) + after)
    # don't cut words in half
    if start > 0:
        space = text.find(" ", start)
        start = space + 1 if 0 <= space < min(positions) else start
    if end < len(text):
        space = text.rfind(" ", min(positions), end)
        end = space if space > 0 else end
    return ("…" if start > 0 else "") + text[start:end] + ("…" if end < len(text) else "")
