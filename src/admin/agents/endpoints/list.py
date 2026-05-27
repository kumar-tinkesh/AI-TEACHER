from typing import List
from fastapi import Depends
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, UserRole
from admin.agents.models import Agent, AgentResponse
from admin.agents.endpoints import router


@router.get(
    "",
    response_model=List[AgentResponse],
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def list_agents(
    all: bool = False,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    List agents.
    Default: agents created by current teacher.
    If ?all=true: all agents with created_by_id info.
    Only accessible by users with the TEACHER role.
    """
    if all:
        agents = db.exec(select(Agent)).all()
    else:
        agents = db.exec(select(Agent).where(Agent.created_by_id == teacher.id)).all()
    return agents
