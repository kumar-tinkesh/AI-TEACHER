from typing import List
from fastapi import Depends
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import RoleChecker
from auth.models import Teacher, UserRole, UserResponse
from auth.routes.endpoints import auth_router, _teacher_to_user_response


@auth_router.get("/teachers", response_model=List[UserResponse], dependencies=[Depends(RoleChecker([UserRole.TEACHER]))])
def list_teachers(
    db: Session = Depends(get_session)
):
    """
    List all registered teachers.
    Only accessible by users with the TEACHER role.
    """
    teachers = db.exec(select(Teacher)).all()
    return [_teacher_to_user_response(t) for t in teachers]
