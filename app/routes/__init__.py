from app.routes.auth import router as auth_router
from app.routes.health import router as health_router
from app.routes.agents import router as agents_router

__all__ = [
    "auth_router",
    "health_router",
    "agents_router",
]
