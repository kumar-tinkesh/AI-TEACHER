import json
from typing import List
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, UserRole
from admin.agents.models import Agent, AgentChunkSearchResponse
from admin.agents.endpoints import router
from core.embeddings import embed_query, cosine_similarity


@router.get(
    "/{agent_id}/search",
    response_model=List[AgentChunkSearchResponse],
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def search_agent_chunks(
    agent_id: int,
    query: str,
    top_k: int = 10,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Semantic search over an agent's chunks.
    Returns top_k most relevant chunks ranked by cosine similarity.
    Uses the separate embeddings column.
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
