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


def _rollback_agent(agent: Agent, db: Session) -> None:
    """Helper to clean up agent record on processing failure."""
    db.delete(agent)
    db.commit()
