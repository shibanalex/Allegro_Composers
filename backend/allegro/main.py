"""Composition root: builds the one application from its modules and wires them together.

    uvicorn allegro.main:app --port 8000

Modules never register themselves; everything that connects one module to another happens here,
in one readable place (see docs/ARCHITECTURE.md).
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import allegro.models  # noqa: F401  (every table on the metadata before the first query)
from allegro.core.config import settings
from allegro.core.errors import register_error_handlers
from allegro.core.storage import storage
from allegro.modules.accounts import api as accounts_api
from allegro.modules.accounts import service as accounts
from allegro.modules.catalog import api as catalog_api
from allegro.modules.catalog import service as catalog
from allegro.modules.discussion import api as discussion_api
from allegro.modules.discussion import service as discussion
from allegro.modules.media import api as media_api
from allegro.modules.publications import api as publications_api
from allegro.modules.publications import service as publications
from allegro.modules.search import api as search_api
from allegro.modules.site import api as site_api

# Uploaded files come from users: never let the browser run one as a page on the site's origin.
# `sandbox` without allow-scripts blocks scripts even in an HTML/SVG file opened directly;
# images, audio and PDFs loaded by the site itself are unaffected. (Same headers in gateway/nginx.conf.)
MEDIA_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; img-src 'self'; media-src 'self'; style-src 'unsafe-inline'; sandbox",
}


def wire_modules() -> None:
    """Connections between modules that go against the dependency direction, as registrations"""
    # Discussion comments on things it doesn't know about: the owners say what exists and who owns it
    discussion.register_target("opus", catalog.resolve_opus_target)
    discussion.register_target("post", publications.resolve_post_target)
    # Profiles show counters kept by other modules
    accounts.register_stat("opuses", catalog.count_opuses)
    accounts.register_stat("performances", catalog.count_performances)
    accounts.register_stat("posts", publications.count_posts)
    accounts.register_stat("articles", publications.count_articles)


def create_app() -> FastAPI:
    app = FastAPI(title="Allegro", version="2.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    wire_modules()
    for module_api in (accounts_api, catalog_api, publications_api, discussion_api, media_api, site_api, search_api):
        app.include_router(module_api.router)

    if storage.is_local:  # in production files are served by the object storage itself
        storage.root.mkdir(parents=True, exist_ok=True)
        app.mount(settings.media_url_prefix, StaticFiles(directory=storage.root), name="media")

        @app.middleware("http")
        async def media_headers(request: Request, call_next):
            response = await call_next(request)
            if request.url.path.startswith(settings.media_url_prefix + "/"):
                response.headers.update(MEDIA_HEADERS)
            return response

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "healthy"}

    return app


app = create_app()
