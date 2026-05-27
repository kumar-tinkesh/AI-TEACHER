from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from auth.database import get_session
from auth.models import Teacher, TeacherRegister, UserResponse
from auth.routes.endpoints import auth_router, logger, _teacher_to_user_response
from auth.security import hash_password
from core.utils import generate_random_id


@auth_router.post("/teacher/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_teacher(user_in: TeacherRegister, db: Session = Depends(get_session)):
    """
    Register a new teacher.
    Teachers can self-register.
    """
    statement = select(Teacher).where(Teacher.username == user_in.username)
    existing_user = db.exec(statement).first()
    if existing_user:
        logger.warning("Teacher registration failed: username '%s' already exists", user_in.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    hashed_pwd = hash_password(user_in.password)

    new_teacher = Teacher(
        id=generate_random_id(db, Teacher, 10000, 99999),
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=hashed_pwd,
        is_active=True,
    )

    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    logger.info("Teacher registered: id=%d username='%s'", new_teacher.id, new_teacher.username)
    return _teacher_to_user_response(new_teacher)
