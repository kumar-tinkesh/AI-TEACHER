from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
import json

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, Student, UserRole, UserResponse
from admin.students.models import StudentUpdate
from admin.students.endpoints import router, logger, _to_user_response, _validate_agent_assignments
from auth.security import hash_password


@router.put(
    "/{student_id}",
    response_model=UserResponse,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def update_student(
    student_id: int,
    student_in: StudentUpdate,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update student credentials/details.
    Only accessible by users with the TEACHER role.
    Can only update students created by this teacher.
    """
    statement = select(Student).where(
        Student.id == student_id,
        Student.teacher_id == teacher.id
    )
    student = db.exec(statement).first()
    if not student:
        logger.warning(
            "Student update failed: id=%d not found or not managed by teacher_id=%d",
            student_id, teacher.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found or not managed by you"
        )

    if student_in.student_name is not None:
        student.full_name = student_in.student_name
    if student_in.age is not None:
        student.age = student_in.age
    if student_in.class_name is not None:
        student.class_name = student_in.class_name
    if student_in.phone_number is not None:
        student.phone_number = student_in.phone_number
    if student_in.is_active is not None:
        student.is_active = student_in.is_active
    if student_in.password is not None:
        student.hashed_password = hash_password(student_in.password)
    if student_in.assigned_agent_ids is not None:
        validated = _validate_agent_assignments(db, teacher.id, student_in.assigned_agent_ids)
        student.assigned_agent_ids = json.dumps(validated)

    db.add(student)
    db.commit()
    db.refresh(student)
    logger.info("Student updated: id=%d by teacher_id=%d", student.id, teacher.id)
    return _to_user_response(student)
