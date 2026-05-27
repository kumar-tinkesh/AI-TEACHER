from typing import List
from fastapi import Depends
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Student, UserRole
from admin.agents.models import Agent
from student.endpoints import router


@router.get(
    "/agents",
    response_model=List[dict],
    dependencies=[Depends(RoleChecker([UserRole.STUDENT]))]
)
def list_student_agents(
    student: Student = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    List all agents assigned to the logged-in student.
    Only accessible by STUDENT role.
    """
    assigned_ids = student.get_assigned_agent_ids()
    if not assigned_ids:
        return []

    agents = db.exec(select(Agent).where(Agent.id.in_(assigned_ids))).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "subject": a.subject,
            "description": a.description,
            "is_active": a.is_active,
            "created_by_id": a.created_by_id,
            "created_at": a.created_at,
        }
        for a in agents
    ]
