import json
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, UserRole
from admin.agents.models import Agent
from admin.agents.endpoints import router, logger
from core.utils import generate_embeddings_for_chunks


@router.post(
    "/{agent_id}/embeddings",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def generate_agent_embeddings(
    agent_id: int,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    (Re)generate embeddings for an agent's chunks.
    Stores them in the separate embeddings column.
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
        chunks = json.loads(agent.chunks) if agent.chunks else []
    except Exception:
        chunks = []

    if not chunks:
        return {"agent_id": agent_id, "embeddings_generated": 0}

    embeddings = generate_embeddings_for_chunks(chunks)
    agent.embeddings = json.dumps(embeddings)
    db.add(agent)
    db.commit()

    logger.info("Embeddings generated: agent_id=%d chunks=%d", agent_id, len(chunks))
    return {"agent_id": agent_id, "embeddings_generated": len(chunks)}
