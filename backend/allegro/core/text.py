"""Cleaning what people type into one-line fields: names, pseudonyms, titles.

- control characters (line breaks, tabs) and invisible «format» characters are removed: zero-width spaces
  make a name look empty, and text-direction overrides (U+202E…) make «Иван‮вонаП» look like someone
  else's name on screen;
- runs of spaces become one, the ends are trimmed;
- the result must contain at least one letter or digit.
"""
import re
import unicodedata

_SPACES = re.compile(r"\s+")


def clean_line(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = "".join(" " if ch in "\n\r\t" else ch for ch in value
                    if unicodedata.category(ch) not in ("Cc", "Cf") or ch in "\n\r\t")
    return _SPACES.sub(" ", value).strip()


def has_meaning(value: str) -> bool:
    return any(ch.isalnum() for ch in value)
