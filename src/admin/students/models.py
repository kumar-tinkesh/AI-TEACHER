from typing import Optional
from sqlmodel import Field, SQLModel

class StudentCreate(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=100)
    student_name: str = Field(min_length=1, max_length=100)
    age: int = Field(gt=0, lt=120)
    class_name: str = Field(min_length=1, max_length=50)
    phone_number: str = Field(min_length=1, max_length=20)

class StudentUpdate(SQLModel):
    password: Optional[str] = Field(default=None, min_length=6, max_length=100)
    student_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    age: Optional[int] = Field(default=None, gt=0, lt=120)
    class_name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    phone_number: Optional[str] = Field(default=None, min_length=1, max_length=20)
    is_active: Optional[bool] = None
