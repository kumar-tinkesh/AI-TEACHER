from typing import List, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select

from auth.database import get_session
from auth.models import Teacher, Student, UserRole
from auth.security import decode_access_token
from core.logging import get_logger

logger = get_logger("auth.deps")

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_session)
):
    """
    Extracts the current authenticated user from the JWT token in request headers.
    Queries Teacher or Student table based on the 'role' claim.
    Ensures the user exists and is active.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        logger.warning("Invalid token presented")
        raise credentials_exception

    username: str = payload.get("sub")
    role: str = payload.get("role")
    if username is None or role is None:
        logger.warning("Token missing 'sub' or 'role' claim")
        raise credentials_exception

    if role == UserRole.TEACHER.value:
        user = db.exec(select(Teacher).where(Teacher.username == username)).first()
    else:
        user = db.exec(select(Student).where(Student.username == username)).first()

    if user is None:
        logger.warning("Token valid but user '%s' not found in database", username)
        raise credentials_exception

    if not user.is_active:
        logger.warning("Access denied for user '%s': account deactivated", username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )

    logger.debug("Authenticated user: '%s' (role=%s)", user.username, role)
    return user


class RoleChecker:
    """
    Dependency factory to restrict endpoint access based on user roles.
    """
    def __init__(self, allowed_roles: List[Union[UserRole, str]]):
        self.allowed_roles = [r.value if isinstance(r, UserRole) else r for r in allowed_roles]

    def __call__(self, current_user = Depends(get_current_user)):
        user_role_val = "teacher" if isinstance(current_user, Teacher) else "student"
        if user_role_val not in self.allowed_roles:
            logger.warning(
                "RBAC denied: user='%s' role='%s' required=%s",
                current_user.username,
                user_role_val,
                self.allowed_roles,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        logger.debug("RBAC allowed: user='%s' role='%s'", current_user.username, user_role_val)
        return current_user
