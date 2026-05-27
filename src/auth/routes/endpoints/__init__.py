import json
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, Student, UserRole, TeacherRegister, UserResponse, Token, UserLogin
from auth.security import hash_password, verify_password, create_access_token
from auth.config import settings
from core.logging import get_logger
from core.utils import generate_random_id

logger = get_logger("auth")
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboards"])
users_router = APIRouter(prefix="/users", tags=["Users"])


def _teacher_to_user_response(teacher):
    return {
        "id": teacher.id,
        "username": teacher.username,
        "full_name": teacher.full_name,
        "role": "teacher",
        "is_active": teacher.is_active,
        "created_at": teacher.created_at,
        "phone_number": teacher.phone_number,
        "age": None,
        "class_name": None,
        "teacher_id": None,
        "assigned_agent_ids": [],
    }


def _to_user_response(user):
    is_teacher = isinstance(user, Teacher)
    assigned = []
    if not is_teacher and getattr(user, "assigned_agent_ids", None):
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
