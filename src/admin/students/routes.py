from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, Student, UserRole, UserResponse
from admin.students.models import StudentCreate, StudentUpdate
from auth.security import hash_password
from core.logging import get_logger
from core.utils import generate_random_id

logger = get_logger("admin.students")
router = APIRouter(prefix="/admin/students", tags=["Admin - Students"])


import json
from admin.agents.models import Agent

def _to_user_response(user):
    is_teacher = isinstance(user, Teacher)
    assigned = []
    if not is_teacher and user.assigned_agent_ids:
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


def _validate_agent_assignments(db, teacher_id, agent_ids):
    if not agent_ids:
        return []
    valid = []
    for aid in agent_ids:
        agent = db.exec(select(Agent).where(Agent.id == aid, Agent.created_by_id == teacher_id)).first()
        if agent:
            valid.append(aid)
        else:
            logger.warning("Agent id=%d not found or not owned by teacher_id=%d", aid, teacher_id)
    return valid


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


@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def delete_student(
    student_id: int,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Delete a student account.
    Only accessible by users with the TEACHER role.
    Can only delete students created by this teacher.
    """
    statement = select(Student).where(
        Student.id == student_id,
        Student.teacher_id == teacher.id
    )
    student = db.exec(statement).first()
    if not student:
        logger.warning(
            "Student deletion failed: id=%d not found or not managed by teacher_id=%d",
            student_id, teacher.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found or not managed by you"
        )

    db.delete(student)
    db.commit()
    logger.info("Student deleted: id=%d username='%s' by teacher_id=%d", student_id, student.username, teacher.id)
    return None
