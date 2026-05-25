from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import User, UserRole, UserResponse
from admin.students.models import StudentCreate, StudentUpdate
from auth.security import hash_password
from core.logging import get_logger

logger = get_logger("admin.students")
router = APIRouter(prefix="/admin/students", tags=["Admin - Students"])

@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def create_student(
    student_in: StudentCreate,
    teacher: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Create a new student credential.
    Only accessible by users with the TEACHER role.
    """
    statement = select(User).where(User.username == student_in.username)
    existing_user = db.exec(statement).first()
    if existing_user:
        logger.warning("Student creation failed: username '%s' already taken", student_in.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    hashed_pwd = hash_password(student_in.password)

    new_student = User(
        username=student_in.username,
        full_name=student_in.student_name,
        hashed_password=hashed_pwd,
        role=UserRole.STUDENT,
        created_by_id=teacher.id,
        is_active=True,
        age=student_in.age,
        class_name=student_in.class_name,
        phone_number=student_in.phone_number,
    )

    db.add(new_student)
    db.commit()
    db.refresh(new_student)
    logger.info(
        "Student created: id=%d username='%s' by teacher_id=%d",
        new_student.id, new_student.username, teacher.id
    )
    return new_student

@router.get(
    "",
    response_model=List[UserResponse],
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def list_students(
    teacher: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    List all students created by the current teacher.
    Only accessible by users with the TEACHER role.
    """
    statement = select(User).where(
        User.role == UserRole.STUDENT,
        User.created_by_id == teacher.id
    )
    students = db.exec(statement).all()
    return students

@router.put(
    "/{student_id}",
    response_model=UserResponse,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def update_student(
    student_id: int,
    student_in: StudentUpdate,
    teacher: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update student credentials/details.
    Only accessible by users with the TEACHER role.
    Can only update students created by this teacher.
    """
    statement = select(User).where(
        User.id == student_id,
        User.role == UserRole.STUDENT,
        User.created_by_id == teacher.id
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

    db.add(student)
    db.commit()
    db.refresh(student)
    logger.info("Student updated: id=%d by teacher_id=%d", student.id, teacher.id)
    return student

@router.delete(
    "/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def delete_student(
    student_id: int,
    teacher: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Delete a student account.
    Only accessible by users with the TEACHER role.
    Can only delete students created by this teacher.
    """
    statement = select(User).where(
        User.id == student_id,
        User.role == UserRole.STUDENT,
        User.created_by_id == teacher.id
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
