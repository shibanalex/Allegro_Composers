"""Factory for service applications - every service is a small FastAPI app on the shared kernel"""
from typing import Iterable

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from allegro_common.config import settings
from allegro_common.storage import storage


# Uploaded files come from users: never let the browser run one as a page on the site's origin.
# `sandbox` without allow-scripts blocks scripts even in an HTML/SVG file opened directly;
# images, audio and PDFs loaded by the site itself are unaffected. (Same headers in gateway/nginx.conf.)
MEDIA_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": "default-src 'none'; img-src 'self'; media-src 'self'; style-src 'unsafe-inline'; sandbox",
}


def create_service(name: str, routers: Iterable[APIRouter], serve_media: bool = False) -> FastAPI:
    app = FastAPI(title=f"Allegro · {name}", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in routers:
        app.include_router(router)

    if serve_media and storage.is_local:  # in production files are served by the object storage itself
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
        return {"status": "healthy", "service": name}

    return app
