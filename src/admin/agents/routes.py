import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, UserRole
from admin.agents.models import Agent, AgentUpdate, AgentResponse, AgentChunkResponse, AgentChunkSearchResponse
from admin.utils.chunker import chunk_bytes
from core.logging import get_logger
from core.utils import generate_random_id, make_chunk_objects, generate_embeddings_for_chunks
from core.embeddings import embed_query, cosine_similarity

logger = get_logger("admin.agents")
router = APIRouter(prefix="/admin/agents", tags=["Admin - Agents"])


@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def create_agent(
    name: str = Form(..., min_length=1, max_length=100),
    subject: str = Form(..., min_length=1, max_length=100),
    class_name: Optional[str] = Form(None, max_length=50),
    description: Optional[str] = Form(None, max_length=500),
    file: UploadFile = File(...),
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Create a new AI agent with an uploaded file.
    File content is read in memory, chunked, and stored in the database for LLM retrieval.
    Only accessible by users with the TEACHER role.
    Accepts multipart/form-data with 'name', 'subject', 'description' and 'file'.
    """
    existing = db.exec(select(Agent).where(Agent.name == name)).first()
    if existing:
        logger.warning("Agent creation failed: name '%s' already taken", name)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent name already taken"
        )

    new_agent = Agent(
        id=generate_random_id(db, Agent, 10000, 99999),
        name=name,
        description=description,
        subject=subject,
        class_name=class_name,
        is_active=True,
        created_by_id=teacher.id,
        chunks="[]",
    )
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)

    try:
        # Read file content in memory
        raw_bytes = file.file.read()
        # Extract text and chunk for LLM context
        chunks = chunk_bytes(raw_bytes, filename=file.filename)
        if chunks:
            chunk_objects = make_chunk_objects(chunks)
            new_agent.chunks = json.dumps(chunk_objects)
            # Generate and store embeddings separately
            embeddings = generate_embeddings_for_chunks(chunk_objects)
            new_agent.embeddings = json.dumps(embeddings)
            db.add(new_agent)
            db.commit()
        logger.info(
            "Agent created: id=%d name='%s' by teacher_id=%d chunks=%d",
            new_agent.id, new_agent.name, teacher.id, len(chunks)
        )
    except Exception:
        logger.error("Agent file processing failed for agent id=%d", new_agent.id, exc_info=True)
        _rollback_agent(new_agent, db)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="File processing failed")
    finally:
        file.file.close()

    return new_agent


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

    # Strip embeddings from response
    for chunk in parsed:
        chunk.pop("embedding", None)
        chunk.pop("score", None)

    return parsed


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

    # Compute similarity against stored embeddings
    scored = []
    for idx, emb in enumerate(embeddings):
        if idx < len(chunks):
            score = cosine_similarity(query_embedding, emb)
            scored.append({**chunks[idx], "score": round(score, 4)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


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


@router.put(
    "/{agent_id}",
    response_model=AgentResponse,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def update_agent(
    agent_id: int,
    agent_in: AgentUpdate,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update an agent's details.
    Only accessible by users with the TEACHER role.
    Can only update agents created by this teacher.
    """
    statement = select(Agent).where(
        Agent.id == agent_id,
        Agent.created_by_id == teacher.id
    )
    agent = db.exec(statement).first()
    if not agent:
        logger.warning(
            "Agent update failed: id=%d not found or not managed by teacher_id=%d",
            agent_id, teacher.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or not managed by you"
        )

    if agent_in.name is not None:
        agent.name = agent_in.name
    if agent_in.description is not None:
        agent.description = agent_in.description
    if agent_in.subject is not None:
        agent.subject = agent_in.subject
    if agent_in.class_name is not None:
        agent.class_name = agent_in.class_name
    if agent_in.is_active is not None:
        agent.is_active = agent_in.is_active

    db.add(agent)
    db.commit()
    db.refresh(agent)
    logger.info("Agent updated: id=%d by teacher_id=%d", agent.id, teacher.id)
    return agent


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker([UserRole.TEACHER]))]
)
def delete_agent(
    agent_id: int,
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Delete an agent and all stored chunks.
    Only accessible by users with the TEACHER role.
    Can only delete agents created by this teacher.
    """
    statement = select(Agent).where(
        Agent.id == agent_id,
        Agent.created_by_id == teacher.id
    )
    agent = db.exec(statement).first()
    if not agent:
        logger.warning(
            "Agent deletion failed: id=%d not found or not managed by teacher_id=%d",
            agent_id, teacher.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or not managed by you"
        )

    db.delete(agent)
    db.commit()
    logger.info(
        "Agent deleted: id=%d name='%s' by teacher_id=%d",
        agent_id, agent.name, teacher.id
    )
    return None


def _rollback_agent(agent: Agent, db: Session) -> None:
    """Helper to clean up agent record on processing failure."""
    db.delete(agent)
    db.commit()
