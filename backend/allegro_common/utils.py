"""Small helpers shared by services"""
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

_TRANSLIT = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i",
    "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t",
    "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "",
    "э": "e", "ю": "yu", "я": "ya",
})


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower().translate(_TRANSLIT)).strip("-")
    return slug[:80] or "untitled"


def unique_slug(db: Session, column, text: str, *filters) -> str:
    """Slug that does not collide with existing values of `column` (optionally within `filters`)"""
    base = slugify(text)
    slug, n = base, 2
    while db.scalar(select(column).where(column == slug, *filters)) is not None:
        slug, n = f"{base}-{n}", n + 1
    return slug


def visible_authors(author_column):
    """SQL condition: the author of the row is not shadowed (hidden accounts vanish from the site)"""
    from allegro_common.models import User

    return author_column.in_(select(User.id).where(User.is_hidden.is_(False)))
