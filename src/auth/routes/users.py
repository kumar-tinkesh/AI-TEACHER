from fastapi import APIRouter, Depends
from auth.dependencies import get_current_user
from auth.models import User, UserResponse

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/me", response_model=UserResponse)
def read_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get profile of the currently authenticated user.
    """
    return current_user
