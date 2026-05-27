import json
from typing import List
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, UserRole
from admin.agents.models import Agent, AgentChunkResponse
from admin.agents.endpoints import router


@router.get(
    "/{agent_id}/chunks",
    response_model=List[AgentChunkResponse],
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def get_agent_chunks(
    agent_id: int,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Retrieve all chunks for a given agent (no embeddings, no scores).
    Only accessible by users with the TEACHER role.
    """
    agent = db.exec(
        select(Agent).where(Agent.id == agent_id, Agent.created_by_id == teacher.id)
    ).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or not managed by you"
        )

    try:
        parsed = json.loads(agent.chunks) if agent.chunks else []
    except Exception:
        parsed = []

    for chunk in parsed:
        chunk.pop("embedding", None)
        chunk.pop("score", None)

    return parsed
