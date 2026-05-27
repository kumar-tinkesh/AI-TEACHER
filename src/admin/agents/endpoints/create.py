import json
from typing import Optional
from fastapi import Depends, HTTPException, status, UploadFile, File, Form
from sqlmodel import Session, select

from auth.database import get_session
from auth.dependencies import get_current_user, RoleChecker
from auth.models import Teacher, UserRole
from admin.agents.models import Agent, AgentResponse
from admin.agents.endpoints import router, logger, _rollback_agent
from admin.utils.chunker import chunk_bytes
from core.utils import generate_random_id, make_chunk_objects, generate_embeddings_for_chunks


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
        raw_bytes = file.file.read()
        chunks = chunk_bytes(raw_bytes, filename=file.filename)
        if chunks:
            chunk_objects = make_chunk_objects(chunks)
            new_agent.chunks = json.dumps(chunk_objects)
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
