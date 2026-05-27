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
