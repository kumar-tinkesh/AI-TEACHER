from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from auth.database import get_session
from auth.models import User, UserRole, UserRegister, UserResponse, Token, UserLogin
from auth.security import hash_password, verify_password, create_access_token
from auth.config import settings
from core.logging import get_logger

logger = get_logger("auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/teacher/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_teacher(user_in: UserRegister, db: Session = Depends(get_session)):
    """
    Register a new teacher (Admin role).
    Teachers can self-register.
    """
    statement = select(User).where(User.username == user_in.username)
    existing_user = db.exec(statement).first()
    if existing_user:
        logger.warning("Teacher registration failed: username '%s' already exists", user_in.username)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    hashed_pwd = hash_password(user_in.password)

    new_teacher = User(
        username=user_in.username,
        full_name=user_in.full_name,
        hashed_password=hashed_pwd,
        role=UserRole.TEACHER,
        is_active=True,
    )

    db.add(new_teacher)
    db.commit()
    db.refresh(new_teacher)
    logger.info("Teacher registered: id=%d username='%s'", new_teacher.id, new_teacher.username)
    return new_teacher

@router.post("/login", response_model=Token)
def login(
    credentials: UserLogin,
    db: Session = Depends(get_session)
):
    """
    Login endpoint.
    Expects JSON body with 'username' and 'password'.
    """
    statement = select(User).where(User.username == credentials.username)
    user = db.exec(statement).first()

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
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires
    )

    logger.info("Login success: username='%s' role='%s'", user.username, user.role.value)
    return {"access_token": access_token, "token_type": "bearer"}
