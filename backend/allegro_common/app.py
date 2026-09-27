"""Factory for service applications - every service is a small FastAPI app on the shared kernel"""
from typing import Iterable

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from allegro_common.config import settings
from allegro_common.storage import storage


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

    if serve_media:
        storage.root.mkdir(parents=True, exist_ok=True)
        app.mount(settings.media_url_prefix, StaticFiles(directory=storage.root), name="media")

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "healthy", "service": name}

    return app
