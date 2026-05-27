import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from auth import create_db_and_tables, auth_router, dashboard_router, users_router
from admin import students_router, agents_router
from student import student_router
from core.logging import setup_logging
from core.embeddings import load_model

setup_logging(level="INFO")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables in the database on startup
    create_db_and_tables()
    # Pre-load embedding model into memory
    load_model()
    yield

app = FastAPI(
    title="AI Teacher Platform API",
    description="Secure Role-Based Authentication & User Management System",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Register routers under /api/v1 prefix
app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(students_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(student_router, prefix="/api/v1")

# Serve static admin UI files (resolved relative to this file)
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

@app.get("/", tags=["Root"])
def root():
    """Redirect root to admin UI if available, otherwise return API info."""
    if os.path.isdir(_static_dir):
        return RedirectResponse(url="/static/index.html")
    return {"message": "Welcome to the AI Teacher Platform API!", "documentation": "/docs"}
