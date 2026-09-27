from allegro_common.app import create_service
from services.media.routes import router

app = create_service("media", [router], serve_media=True)
