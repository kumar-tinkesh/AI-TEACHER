from fastapi import Depends
from auth.dependencies import RoleChecker
from auth.models import UserRole
from auth.routes.endpoints import dashboard_router


@dashboard_router.get(
    "/shared",
    dependencies=[Depends(RoleChecker([UserRole.TEACHER, UserRole.STUDENT]))]
)
def shared_dashboard():
    """
    Shared dashboard accessible by both teachers and students.
    """
    return {
        "message": "Welcome to the Shared Workspace!",
        "info": "This content is visible to both Teachers and Students."
    }
