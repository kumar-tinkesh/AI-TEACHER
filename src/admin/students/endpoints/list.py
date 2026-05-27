from typing import List
from fastapi import Depends
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, Student, UserRole, UserResponse
from admin.students.endpoints import router, _to_user_response


@router.get(
    "",
    response_model=List[UserResponse],
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def list_students(
    all: bool = False,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    List students.
    Default: students created by current teacher.
    If ?all=true: all students with teacher_id info.
    Only accessible by users with the TEACHER role.
    """
    if all:
        students = db.exec(select(Student)).all()
    else:
        students = db.exec(select(Student).where(Student.teacher_id == teacher.id)).all()
    return [_to_user_response(s) for s in students]
