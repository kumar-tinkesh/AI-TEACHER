from contextlib import asynccontextmanager
from fastapi import FastAPI
from auth import create_db_and_tables, auth_router, dashboard_router, users_router
from admin import students_router, agents_router
from core.logging import setup_logging

setup_logging(level="INFO")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables in the database on startup
    create_db_and_tables()
    yield

app = FastAPI(
    title="AI Teacher Platform API",
    description="Secure Role-Based Authentication & User Management System",
    version="1.0.0",
    lifespan=lifespan
)

# Register routers under /api/v1 prefix
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(students_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")

@app.get("/", tags=["Root"])
def root():
    """
    Root endpoint directing users to API documentation.
    """
    return {
        "message": "Welcome to the AI Teacher Platform API!",
        "documentation": "/docs"
    }
