from admin.students.endpoints import router
from admin.students.endpoints import create, list, update, delete
from admin.students.models import StudentCreate, StudentUpdate

__all__ = [
    "router",
    "StudentCreate",
    "StudentUpdate",
]