from typing import List
import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, Student, UserRole, UserResponse
from admin.agents.models import Agent
from admin.students.models import StudentCreate, StudentUpdate
from auth.security import hash_password
from core.logging import get_logger
from core.utils import generate_random_id

logger = get_logger("admin.students")
router = APIRouter(prefix="/admin/students", tags=["Admin - Students"])


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
