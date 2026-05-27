from datetime import timedelta
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from auth.database import get_session
from auth.models import Teacher, Student, Token, UserLogin
from auth.routes.endpoints import auth_router, logger
from auth.security import verify_password, create_access_token
from auth.config import settings


@auth_router.post("/login", response_model=Token)
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
