# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Teacher Platform — a role-based FastAPI application where teachers manage students and AI knowledge agents, and students query assigned agents using semantic search. Uses SQLModel + SQLite, sentence-transformers for embeddings, and litellm/ollama/groq for LLM inference.

## Common Commands

- `make setup` — install `uv` (if missing), create `.venv`, and sync all dependencies.
- `make install` — re-sync dependencies (`uv sync --all-groups`).
- `make dev` — start the FastAPI server with auto-reload (`cd src && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload`).
- `make run` — start the production server (`cd src && uv run uvicorn main:app --host 0.0.0.0 --port 8000`).
- `make test` — run the pytest suite (`uv run pytest tests/ -v`).
- `make clean` — remove `.venv`, `__pycache__`, `.pytest_cache`, and `*.pyc`.

Run a single test with `uv run pytest tests/test_auth.py::test_name -v`.

## Architecture

### Entry Point

`src/main.py` creates the FastAPI app, registers all routers under `/api/v1`, serves `src/static/` at `/static`, and defines a lifespan that:
1. creates SQLModel tables via `auth.database.create_db_and_tables()`, and
2. eagerly loads the sentence-transformer model via `core.embeddings.load_model()`.

### Router Organization

Routers are grouped by domain and imported into `main.py`:
- **Auth** (`src/auth/`) — login, teacher self-registration, `/me`, dashboards, teacher listing.
- **Admin** (`src/admin/`) — teacher-only endpoints for student CRUD (`src/admin/students/`) and agent CRUD + search (`src/admin/agents/`).
- **Student** (`src/student/`) — student-facing endpoints to list assigned agents and perform semantic search.

Each endpoint lives in its own small file under `endpoints/`. Router objects are exported from domain-level `__init__.py` files.

### Authentication & RBAC

- `auth.security` handles bcrypt hashing and JWT encode/decode.
- `auth.dependencies.get_current_user` decodes the Bearer token, looks up the user in `Teacher` or `Student` tables based on the `role` claim, and rejects inactive accounts.
- `auth.dependencies.RoleChecker(allowed_roles)` restricts endpoints. Student endpoints use it; admin endpoints rely on the same checker or direct role checks in route logic.
- Token expiry is 30 minutes by default.

### Data Models

All models use SQLModel:
- `Teacher` — self-registered; owns students and agents.
- `Student` — created by a teacher; `teacher_id` foreign key; `assigned_agent_ids` stored as a JSON list string.
- `Agent` — created by a teacher; stores chunked text and per-chunk embeddings as JSON strings in the row.

Database configuration lives in `auth.config.Settings` (reads from `.env` or defaults to SQLite at `sqlite:///./ai_teacher.db`).

### Document Processing Pipeline

1. Teacher uploads a file via `POST /api/v1/admin/agents` as multipart form data.
2. `admin.utils.chunker.chunk_bytes()` extracts text: PDF via PyMuPDF (`fitz`), plain text with multiple encoding fallback.
3. `split_into_chunks()` produces ~1000-character chunks with 200-character overlap, splitting at word/newline boundaries.
4. `core.utils` generates chunk objects + embeddings, stored as JSON in the `Agent` row.

### Semantic Search

- `core.embeddings.embed_texts()` / `embed_query()` use `sentence-transformers/all-MiniLM-L6-v2`.
- `rank_chunks_by_similarity()` computes cosine similarity between the query embedding and each chunk embedding.
- Teachers can search any of their agents (`/admin/agents/{id}/search`). Students can only search agents in their `assigned_agent_ids` (`/agents/{id}/search`).

### LLM Clients

`llm-proxy/llm.py` provides thin wrappers:
- `OllamaCloudClient` — uses the `ollama` SDK with env-configured host, API key, and model.
- `GroqCloudClient` — uses the `openai` SDK with env-configured base URL, API key, model, temperature, and max tokens.
- Both support an optional `SYSTEM_PROMPT` from environment variables.

### Frontend

A vanilla JS single-page admin dashboard is served from `src/static/index.html` and `src/static/admin.js`. It supports teacher registration, login, student CRUD, agent creation with file upload, chunk viewing, and semantic search.

## Key Files for Debugging

- `auth/config.py` — DB URL, JWT secret, algorithm, expiry.
- `auth/database.py` — engine, session factory, table creation.
- `core/embeddings.py` — model loading, embedding, similarity ranking.
- `admin/utils/chunker.py` — text extraction and chunking logic.
- `core/utils.py` — random ID generation, chunk object builder, embedding generation helper.
- `llm-proxy/llm.py` — LLM provider client wrappers.

## Environment Variables

The app respects these env vars (with defaults):
- `DATABASE_URL` — default `sqlite:///./ai_teacher.db`
- `JWT_SECRET_KEY` — default hardcoded dev secret
- `JWT_ALGORITHM` — default `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES` — default `30`
- `SYSTEM_PROMPT` — optional, injected into LLM client calls
