.PHONY: setup install run test clean dev help

PYTHON := python3.11
VENV := .venv
UV := $(shell command -v uv 2>/dev/null)

help:
	@echo "Available targets:"
	@echo "  make setup   - Create venv and install all dependencies"
	@echo "  make install - Install/update dependencies"
	@echo "  make run     - Start the FastAPI server"
	@echo "  make dev     - Start server with auto-reload (development)"
	@echo "  make test    - Run all tests"
	@echo "  make clean   - Remove venv and cache files"

setup:
	@echo "Setting up project..."
	@if [ -z "$(UV)" ]; then \
		echo "uv not found. Installing uv..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	fi
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		uv venv --python $(PYTHON); \
	fi
	@echo "Installing dependencies..."
	uv sync
	@echo "Setup complete. Run 'make run' to start the server."

install:
	@echo "Installing dependencies..."
	uv sync

run:
	@echo "Starting AI Teacher Platform API..."
	@echo "Loading embedding model (first run may take a moment)..."
	cd src && uv run uvicorn main:app --host 0.0.0.0 --port 8000

dev:
	@echo "Starting AI Teacher Platform API (dev mode with reload)..."
	cd src && uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

test:
	@echo "Running tests..."
	uv run pytest tests/ -v

clean:
	@echo "Cleaning up..."
	rm -rf $(VENV)
	rm -rf src/__pycache__ src/*/__pycache__ src/*/*/__pycache__
	rm -rf tests/__pycache__
	rm -rf .pytest_cache
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	@echo "Clean complete."
