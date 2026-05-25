import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, UserRole
from admin.agents.models import Agent, AgentUpdate, AgentResponse, AgentChunkResponse
from admin.utils.chunker import chunk_bytes
from core.logging import get_logger
from core.utils import generate_random_id, make_chunk_objects

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
    teacher: Teacher = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    List all agents created by the current teacher.
    Only accessible by users with the TEACHER role.
    """
    statement = select(Agent).where(Agent.created_by_id == teacher.id)
    agents = db.exec(statement).all()
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
    Retrieve all chunks for a given agent.
    Only accessible by users with the TEACHER role.
    Can only access agents created by this teacher.
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
    return parsed


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
