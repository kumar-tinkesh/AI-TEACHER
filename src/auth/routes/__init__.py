from auth.routes.endpoints import auth_router, dashboard_router, users_router
from auth.routes.endpoints import (
    register,
    login,
    list_teachers,
    teacher_dashboard,
    student_dashboard,
    shared_dashboard,
    me,
)

__all__ = [
    "auth_router",
    "dashboard_router",
    "users_router",
]
