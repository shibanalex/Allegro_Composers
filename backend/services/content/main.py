from allegro_common.app import create_service
from services.content.materials import router as materials
from services.content.routes import router

app = create_service("content", [router, materials])
