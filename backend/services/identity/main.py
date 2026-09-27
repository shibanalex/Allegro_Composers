from allegro_common.app import create_service
from services.identity.routes import router

app = create_service("identity", [router])
