"""Local development: every service's routes in one process on :8000.

In docker-compose each service runs in its own container behind the nginx gateway;
the routes and the shared database are identical, so the frontend can't tell the difference.

    python dev_server.py
"""
from allegro_common.app import create_service
from services.catalog.routes import router as catalog
from services.content.materials import router as materials
from services.content.routes import router as content
from services.discussion.routes import router as discussion
from services.identity.routes import router as identity
from services.media.routes import router as media

app = create_service("all-in-one", [identity, catalog, content, materials, discussion, media], serve_media=True)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("dev_server:app", host="127.0.0.1", port=8000, reload=True)
