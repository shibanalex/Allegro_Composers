from allegro_common.app import create_service
from services.catalog.routes import router

app = create_service("catalog", [router])
