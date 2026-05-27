from fastapi import Depends
from auth.dependencies import RoleChecker
from auth.models import UserRole
from auth.routes.endpoints import dashboard_router


@dashboard_router.get(
    "/teacher",
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def teacher_dashboard():
    """
    Teacher-only dashboard.
    Only accessible by users with the TEACHER role.
    """
    return {
        "message": "Welcome to the Teacher (Admin) Dashboard!",
        "actions_available": [
            "Create student accounts",
            "View student list",
            "Update student details",
            "Reset student passwords",
            "Deactivate/delete student accounts"
        ]
    }
