from datetime import datetime
from enum import Enum
from typing import Optional, Union
from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    TEACHER = "teacher"
    STUDENT = "student"


# --- Database Tables ---

class Teacher(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, min_length=3, max_length=50)
    hashed_password: str
    full_name: str = Field(min_length=1, max_length=100)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Student(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, min_length=3, max_length=50)
    hashed_password: str
    full_name: str = Field(min_length=1, max_length=100)
    age: Optional[int] = Field(default=None)
    class_name: Optional[str] = Field(default=None, max_length=50)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    teacher_id: Optional[int] = Field(default=None, foreign_key="teacher.id")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Unified type for dependencies
User = Union[Teacher, Student]


# --- API Schemas ---

class TeacherRegister(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    full_name: str = Field(min_length=1, max_length=100)


class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(SQLModel):
    username: Optional[str] = None
    role: Optional[str] = None


class UserLogin(SQLModel):
    username: str
    password: str


class UserResponse(SQLModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    phone_number: Optional[str] = None
    age: Optional[int] = None
    class_name: Optional[str] = None
    teacher_id: Optional[int] = None
