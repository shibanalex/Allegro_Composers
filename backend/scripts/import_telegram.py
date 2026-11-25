"""Import a Telegram channel into a composer's blog («Блог» in their hall).

Takes a Telegram Desktop export in HTML format (messages.html + photos/, files/, video_files/ …).
Works with an export of the channel itself or of its linked discussion chat: only the channel's own
posts are imported; replies in the chat and other people's comments are skipped.

    python -m scripts.import_telegram "../Moments Musicaux" --user allegro_cantabile --dry-run
    python -m scripts.import_telegram "../Moments Musicaux" --user allegro_cantabile --skip 173

Safe to run again: posts are matched by their Telegram message number (slug tg-<id>) and updated,
so a later export *with media* adds the photos, audio and files to the posts that already exist.
Needs beautifulsoup4 (pip install -r requirements-tools.txt).
"""
import argparse
import mimetypes
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup, NavigableString, Tag
from sqlalchemy import select

import allegro.models  # noqa: F401  (all tables, for relationships)
from allegro.core.db import SessionLocal
from allegro.core.storage import storage
from allegro.modules.accounts.models import User
from allegro.modules.publications.models import Post

MEDIA_LINK_CLASSES = ("media", "photo_wrap", "video_file_wrap", "animated_wrap", "sticker_wrap")


@dataclass
class Message:
    id: int
    author: str
    date: datetime
    markdown: str
    media: list[dict] = field(default_factory=list)  # {kind, name, path (Path|None), note}
    is_reply: bool = False


# ---------------------------------------------------------------- HTML → Markdown

def _markdown(node) -> str:
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ""
    inner = "".join(_markdown(child) for child in node.children)
    name = node.name
    if name == "br":
        return "\n"
    if name in ("strong", "b"):
        return f"**{inner.strip()}**" if inner.strip() else inner
    if name in ("em", "i"):
        return f"*{inner.strip()}*" if inner.strip() else inner
    if name in ("s", "strike", "del"):
        return f"~~{inner}~~"
    if name == "code":
        return f"`{inner}`"
    if name == "pre":
        return f"\n```\n{node.get_text()}\n```\n"
    if name == "blockquote":
        return "\n" + "\n".join("> " + line for line in inner.strip().splitlines()) + "\n\n"
    if name == "a":
        href = node.get("href", "")
        text = inner.strip()
        if not href or href.startswith("#"):
            return inner
        if not text or text == href or text in href:
            return href  # a bare link: the site turns it into a link itself
        return f"[{text}]({href})"
    return inner  # span (spoilers, emoji), u, etc.


def _clean(md: str) -> str:
    md = md.replace("\xa0", " ")
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


# ---------------------------------------------------------------- parsing

def _date(value: str) -> datetime:
    # "06.02.2026 14:05:20 UTC+03:00"
    parsed = datetime.strptime(value.replace("UTC", ""), "%d.%m.%Y %H:%M:%S %z")
    return parsed.astimezone(timezone.utc)


def parse_export(folder: Path) -> list[Message]:
    html_files = sorted(folder.glob("messages*.html"), key=lambda p: int(re.sub(r"\D", "", p.stem) or 0))
    messages: list[Message] = []
    last_author = ""
    for html in html_files:
        soup = BeautifulSoup(html.read_text(encoding="utf-8"), "html.parser")
        for div in soup.select("div.message.default"):
            body = div.select_one("div.body")
            name = body.select_one("div.from_name")
            if name:
                for extra in name.select("span"):
                    extra.decompose()
                last_author = name.get_text(" ", strip=True)
            date_el = body.select_one("div.date[title]")
            text_el = body.select_one("div.text")
            media = []
            for wrap in body.select("div.media_wrap"):
                for el in wrap.find_all(["a", "div"], recursive=False):
                    classes = el.get("class", [])
                    kind = next((c for c in classes if c.startswith("media_")), None) or next(
                        (c for c in classes if c in MEDIA_LINK_CLASSES), "media")
                    title = el.select_one("div.title")
                    desc = el.select_one("div.description")
                    href = el.get("href") if el.name == "a" else None
                    path = (folder / href) if href and not href.startswith(("http", "#")) else None
                    media.append({
                        "kind": kind.replace("media_", "").replace("_wrap", ""),
                        "name": (title.get_text(" ", strip=True) if title else "") or (Path(href).name if href else ""),
                        "path": path if path and path.is_file() else None,
                        "note": desc.get_text(" ", strip=True) if desc else "",
                    })
            messages.append(Message(
                id=int(div["id"].replace("message", "")),
                author=last_author,
                date=_date(date_el["title"]) if date_el else datetime.now(timezone.utc),
                markdown=_clean(_markdown(text_el)) if text_el else "",
                media=media,
                is_reply=bool(body.select_one("div.reply_to")),
            ))
    return messages


def _chat_reply(messages: list[Message], i: int, channel: str) -> bool:
    """A short text-only line written right after someone else spoke in the chat is a reply in a
    conversation, not a channel post (Telegram doesn't always mark those as replies)"""
    m = messages[i]
    if m.media or len(m.markdown) >= 60:
        return False
    for other in reversed(messages[:i]):
        if (m.date - other.date).total_seconds() > 600:
            return False
        if other.author != channel:
            return True
    return False


def channel_posts(messages: list[Message], channel: str) -> list[list[Message]]:
    """The channel's own posts (no chat replies), with messages sent together merged into one post"""
    own = [
        m for i, m in enumerate(messages)
        if m.author == channel and not m.is_reply and not _chat_reply(messages, i, channel)
    ]
    groups: list[list[Message]] = []
    for m in own:
        if groups and groups[-1][-1].date == m.date:  # an album or a long post split by Telegram
            groups[-1].append(m)
        else:
            groups.append([m])
    return groups


# ---------------------------------------------------------------- import

def _attachment(item: dict, folder_key: str) -> Optional[dict]:
    path: Optional[Path] = item["path"]
    if not path:
        return None
    key = f"{folder_key}/{path.name}"
    if not storage.exists(key):
        storage.save_bytes(key, path.read_bytes())
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return {"url": storage.url(key), "name": item["name"] or path.name, "content_type": content_type, "size": path.stat().st_size}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path, help="folder of the Telegram HTML export")
    parser.add_argument("--user", required=True, help="username whose blog receives the posts")
    parser.add_argument("--channel", help="author name of the channel posts (default: the most frequent author)")
    parser.add_argument("--skip", type=int, nargs="*", default=[], help="Telegram message numbers to leave out")
    parser.add_argument("--dry-run", action="store_true", help="only show what would be imported")
    args = parser.parse_args()

    messages = parse_export(args.folder)
    channel = args.channel or Counter(m.author for m in messages).most_common(1)[0][0]
    groups = channel_posts([m for m in messages if m.id not in set(args.skip)], channel)

    missing = Counter()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == args.user.lower()))
        if not user:
            raise SystemExit(f"Нет пользователя {args.user}")
        created = updated = skipped = 0
        for group in groups:
            first = group[0]
            text = "\n\n".join(m.markdown for m in group if m.markdown)
            attachments = []
            for m in group:
                for item in m.media:
                    att = _attachment(item, f"tg/{user.username}")
                    if att:
                        attachments.append(att)
                    else:
                        missing[item["kind"]] += 1
            if not text and not attachments:
                skipped += 1  # media only, and the media is not in this export
                continue
            slug = f"tg-{first.id}"
            post = db.scalar(select(Post).where(Post.slug == slug))
            if post and post.author_id != user.id:
                raise SystemExit(f"Слаг {slug} уже занят чужой публикацией")
            if args.dry_run:
                created += post is None
                updated += post is not None
                continue
            if post is None:
                post = Post(author_id=user.id, kind="note", title="", slug=slug, tags=[], status="published", view_count=0)
                db.add(post)
                created += 1
            else:
                updated += 1
            post.content_md = text
            known = {a["url"] for a in post.attachments or []}
            post.attachments = [*(post.attachments or []), *(a for a in attachments if a["url"] not in known)]
            post.created_at = post.updated_at = first.date
        if not args.dry_run:
            db.commit()

    print(f"Канал: «{channel}» — постов {len(groups)} (из {sum(len(g) for g in groups)} сообщений)")
    print(f"{'Будет создано' if args.dry_run else 'Создано'}: {created}, обновлено: {updated}, пропущено без текста и медиа: {skipped}")
    if missing:
        print("Медиа нет в выгрузке (экспортируйте заново с фото, видео, аудио и файлами):",
              ", ".join(f"{k} — {n}" for k, n in missing.most_common()))


if __name__ == "__main__":
    main()
