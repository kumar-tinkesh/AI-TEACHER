from fastapi import Depends
from auth.dependencies import get_current_user
from auth.models import UserResponse
from auth.routes.endpoints import users_router, _to_user_response


@users_router.get("/me", response_model=UserResponse)
def read_current_user_profile(current_user = Depends(get_current_user)):
    """
    Get profile of the currently authenticated user.
    """
    return _to_user_response(current_user)
