"""Search by words across the site: a read-only composition of the other modules' public search functions"""
from sqlalchemy.orm import Session

from allegro.core import textsearch
from allegro.modules.accounts.service import search_members
from allegro.modules.catalog.service import popular_instruments, search_opuses
from allegro.modules.publications.service import search_posts
from allegro.modules.search.schemas import SearchComposer, SearchOpus, SearchPost, SearchResult


def search(db: Session, q: str, limit: int) -> SearchResult:
    words = textsearch.stems(q)
    if not words:
        return SearchResult(composers=[], opuses=[], posts=[], instruments=[], words=[])
    instruments = [i for i in popular_instruments(db) if all(w in i for w in words)][:limit]
    return SearchResult(
        composers=[SearchComposer.model_validate(u) for u in search_members(db, words, limit)],
        opuses=[SearchOpus(
            slug=o.slug, title=o.title, subtitle=o.subtitle, author=o.author,
            snippet=textsearch.snippet(o.description_md or "", words) if o.description_md else None,
        ) for o in search_opuses(db, words, limit)],
        posts=[SearchPost(
            slug=p.slug, title=p.title, kind=p.kind, author=p.author, created_at=p.created_at,
            snippet=textsearch.snippet(p.content_md or "", words),
        ) for p in search_posts(db, words, limit)],
        instruments=instruments,
        words=words,
    )
