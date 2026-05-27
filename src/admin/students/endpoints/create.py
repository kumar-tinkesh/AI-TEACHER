from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
import json

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, Student, UserRole, UserResponse
from admin.students.models import StudentCreate
from admin.students.endpoints import router, logger, _to_user_response, _validate_agent_assignments
from auth.security import hash_password
from core.utils import generate_random_id


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def create_student(
    student_in: StudentCreate,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Create a new student credential.
    Only accessible by users with the TEACHER role.
    """
    statement = select(Student).where(Student.username == student_in.username)
    existing_user = db.exec(statement).first()
    if existing_user:
        logger.warning("Student creation failed: username '%s' already taken", student_in.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    hashed_pwd = hash_password(student_in.password)

    validated_agents = _validate_agent_assignments(db, teacher.id, student_in.assigned_agent_ids)

    new_student = Student(
        id=generate_random_id(db, Student, 10000, 99999),
        username=student_in.username,
        full_name=student_in.student_name,
        hashed_password=hashed_pwd,
        teacher_id=teacher.id,
        is_active=True,
        age=student_in.age,
        class_name=student_in.class_name,
        phone_number=student_in.phone_number,
        assigned_agent_ids=json.dumps(validated_agents),
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    logger.info(
        "Student created: id=%d username='%s' by teacher_id=%d agents=%s",
        new_student.id, new_student.username, teacher.id, validated_agents
    )
    return _to_user_response(new_student)
