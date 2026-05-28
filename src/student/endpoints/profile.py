from fastapi import Depends
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Student, UserRole, UserResponse
from student.endpoints import router
from auth.routes.endpoints import _to_user_response


@router.get(
    "/me",
    response_model=UserResponse,
    dependencies=[Depends(RoleChecker([UserRole.STUDENT]))]
)
def read_student_profile(current_user: Student = Depends(get_current_user)):
    """
    Get profile of the currently authenticated student.
    Only accessible by STUDENT role.
    """
    return _to_user_response(current_user)
