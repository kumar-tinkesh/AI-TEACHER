  ┌──────────────┬─────────────────────────────────────────────────────────────────────────┐
  │   Command    │                              What it does                               │
  ├──────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ make setup   │ Creates .venv if missing, installs uv if needed, syncs all dependencies │
  ├──────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ make install │ Re-syncs dependencies                                                   │
  ├──────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ make run     │ Starts server on http://localhost:8000                                  │
  ├──────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ make dev     │ Starts server with --reload for development                             │
  ├──────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ make test    │ Runs pytest tests/ -v                                                   │
  ├──────────────┼─────────────────────────────────────────────────────────────────────────┤
  │ make clean   │ Removes .venv, __pycache__, .pytest_cache                               │
  └──────────────┴─────────────────────────────────────────────────────────────────────────┘

  Verified working:
  - Swagger docs at http://localhost:8000/docs are accessible

  Usage:
  # One-time setup
  make setup

  # Start the server
  make run

  # Or development mode with auto-reload
  make dev