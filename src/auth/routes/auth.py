from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from typing import List
from auth.database import get_session
from auth.dependencies import RoleChecker
from auth.models import Teacher, Student, UserRole, TeacherRegister, UserResponse, Token, UserLogin
from auth.security import hash_password, verify_password, create_access_token
from auth.config import settings
from core.logging import get_logger
from core.utils import generate_random_id

logger = get_logger("auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/teacher/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
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
    return {
        "id": new_teacher.id,
        "username": new_teacher.username,
        "full_name": new_teacher.full_name,
        "role": "teacher",
        "is_active": new_teacher.is_active,
        "created_at": new_teacher.created_at,
        "phone_number": new_teacher.phone_number,
        "age": None,
        "class_name": None,
        "teacher_id": None,
    }


@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_session)
):
    """
    Login endpoint.
    Expects JSON body with 'username' and 'password'.
    """
    user = db.exec(select(Teacher).where(Teacher.username == credentials.username)).first()
    role = "teacher"

    if not user:
        user = db.exec(select(Student).where(Student.username == credentials.username)).first()
        role = "student"

    if not user or not verify_password(credentials.password, user.hashed_password):
        logger.warning("Login failed for username='%s': invalid credentials", credentials.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        logger.warning("Login blocked for username='%s': account deactivated", credentials.username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is deactivated"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": role},
        expires_delta=access_token_expires
    )

    logger.info("Login success: username='%s' role='%s'", user.username, role)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/teachers", response_model=List[UserResponse], dependencies=[Depends(RoleChecker([UserRole.TEACHER]))])
def list_teachers(
    db: Session = Depends(get_session)
):
    """
    List all registered teachers.
    Only accessible by users with the TEACHER role.
    """
    teachers = db.exec(select(Teacher)).all()
    return [
        {
            "id": t.id,
            "username": t.username,
            "full_name": t.full_name,
            "role": "teacher",
            "is_active": t.is_active,
            "created_at": t.created_at,
            "phone_number": t.phone_number,
            "age": None,
            "class_name": None,
            "teacher_id": None,
        }
        for t in teachers
    ]
