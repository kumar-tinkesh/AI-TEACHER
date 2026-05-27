from fastapi import Depends
from auth.dependencies import RoleChecker
from auth.models import UserRole
from auth.routes.endpoints import dashboard_router


@dashboard_router.get(
    "/student",
    dependencies=[Depends(RoleChecker([UserRole.STUDENT]))]
)
def student_dashboard():
    """
    Student-only dashboard.
    Only accessible by users with the STUDENT role.
    """
    return {
        "message": "Welcome to the Student Dashboard!",
        "actions_available": [
            "View curriculum",
            "Submit assignments",
            "Check grading feedback"
        ]
    }
