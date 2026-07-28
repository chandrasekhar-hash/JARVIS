from routes.auth_routes import router as auth_router
from routes.device_routes import router as device_router
from routes.identity_routes import router as identity_router
from routes.health_routes import router as health_router

__all__ = ["auth_router", "device_router", "identity_router", "health_router"]
