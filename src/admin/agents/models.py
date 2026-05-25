from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class Agent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    subject: str = Field(min_length=1, max_length=100)
    is_active: bool = Field(default=True)
    created_by_id: Optional[int] = Field(default=None, foreign_key="teacher.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    chunks: str = Field(default="[]", sa_column=Column(Text))
    embeddings: str = Field(default="[]", sa_column=Column(Text))


class AgentCreate(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    subject: str = Field(min_length=1, max_length=100)


class AgentUpdate(SQLModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    subject: Optional[str] = Field(default=None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


class AgentResponse(SQLModel):
    id: int
    name: str
    description: Optional[str] = None
    subject: str
    is_active: bool
    created_by_id: Optional[int] = None
    created_at: datetime


class AgentChunkResponse(SQLModel):
    id: int
    chunk_index: int
    content: str
    created_at: datetime


class AgentChunkSearchResponse(SQLModel):
    id: int
    chunk_index: int
    content: str
    created_at: datetime
    score: float
