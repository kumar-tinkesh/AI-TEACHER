import json
from fastapi import APIRouter, Depends
from auth.dependencies import get_current_user
from auth.models import Teacher, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


def _to_user_response(user):
    is_teacher = isinstance(user, Teacher)
    assigned = []
    if not is_teacher and getattr(user, "assigned_agent_ids", None):
        try:
            assigned = json.loads(user.assigned_agent_ids)
        except Exception:
            assigned = []
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": "teacher" if is_teacher else "student",
        "is_active": user.is_active,
        "created_at": user.created_at,
        "phone_number": user.phone_number,
        "age": getattr(user, "age", None),
        "class_name": getattr(user, "class_name", None),
        "teacher_id": getattr(user, "teacher_id", None),
        "assigned_agent_ids": assigned,
    }


@router.get("/me", response_model=UserResponse)
def read_current_user_profile(current_user = Depends(get_current_user)):
    """
    Get profile of the currently authenticated user.
    """
    return _to_user_response(current_user)
