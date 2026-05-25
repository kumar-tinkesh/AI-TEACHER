from auth.routes.auth import router as auth_router
from auth.routes.dashboard import router as dashboard_router
from auth.routes.users import router as users_router

__all__ = [
    "auth_router",
    "dashboard_router",
    "users_router",
]
