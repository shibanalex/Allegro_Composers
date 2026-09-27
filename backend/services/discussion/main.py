from allegro_common.app import create_service
from services.discussion.routes import router

app = create_service("discussion", [router])
