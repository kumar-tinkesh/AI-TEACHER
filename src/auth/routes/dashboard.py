from fastapi import APIRouter, Depends
from auth.dependencies import RoleChecker
from auth.models import UserRole

router = APIRouter(prefix="/dashboard", tags=["Dashboards"])

@router.get(
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

@router.get(
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

@router.get(
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
