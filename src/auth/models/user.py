from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel

class UserRole(str, Enum):
    TEACHER = "teacher"
    STUDENT = "student"

class UserBase(SQLModel):
    username: str = Field(index=True, unique=True, min_length=3, max_length=50)
    full_name: str = Field(min_length=1, max_length=100)
    role: UserRole = Field(default=UserRole.STUDENT)
    is_active: bool = Field(default=True)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_by_id: Optional[int] = Field(default=None, foreign_key="user.id", nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    age: Optional[int] = Field(default=None)
    class_name: Optional[str] = Field(default=None, max_length=50)
    phone_number: Optional[str] = Field(default=None, max_length=20)

# API schemas for serialization/validation

class UserRegister(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    full_name: str = Field(min_length=1, max_length=100)

class UserResponse(SQLModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    created_by_id: Optional[int] = None
    is_active: bool
    created_at: datetime
    age: Optional[int] = None
    class_name: Optional[str] = None
    phone_number: Optional[str] = None

class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(SQLModel):
    username: Optional[str] = None
    role: Optional[str] = None

class UserLogin(SQLModel):
    username: str
    password: str
