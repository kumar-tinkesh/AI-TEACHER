from admin.students.routes import router as students_router
from admin.students.models import StudentCreate, StudentUpdate
from admin.agents.routes import router as agents_router

__all__ = [
    "students_router",
    "agents_router",
    "StudentCreate",
    "StudentUpdate",
]
