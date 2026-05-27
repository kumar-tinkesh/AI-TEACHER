from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
import json

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Student, UserRole
from admin.agents.models import Agent, AgentChunkSearchResponse
from core.embeddings import embed_query, cosine_similarity
from core.logging import get_logger

logger = get_logger("student")
router = APIRouter(prefix="/student", tags=["Student"])


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


@router.get(
    "/agents/{agent_id}/search",
    response_model=List[AgentChunkSearchResponse],
    dependencies=[Depends(RoleChecker([UserRole.STUDENT]))]
)
def search_student_agent_chunks(
    agent_id: int,
    query: str,
    top_k: int = 10,
    student: Student = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Semantic search over an assigned agent's chunks.
    Only accessible by STUDENT role.
    """
    assigned_ids = student.get_assigned_agent_ids()
    if agent_id not in assigned_ids:
        logger.warning(
            "Student id=%d attempted to access unassigned agent id=%d",
            student.id, agent_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this agent"
        )

    agent = db.exec(select(Agent).where(Agent.id == agent_id)).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    try:
        chunks = json.loads(agent.chunks) if agent.chunks else []
        embeddings = json.loads(agent.embeddings) if agent.embeddings else []
    except Exception:
        chunks = []
        embeddings = []

    if not chunks or not embeddings:
        return []

    query_embedding = embed_query(query)

    scored = []
    for idx, emb in enumerate(embeddings):
        if idx < len(chunks):
            score = cosine_similarity(query_embedding, emb)
            scored.append({**chunks[idx], "score": round(score, 4)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
