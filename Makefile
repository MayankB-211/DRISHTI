# DRISHTI developer commands.
# Run from the repository root. Backend imports are relative to backend/.

# Prefer 3.12+ (macOS system python3 is often 3.9). Override with: make PYTHON=python3.12
export PATH := $(HOME)/.local/bin:$(PATH)
PYTHON ?= $(shell command -v python3.12 || command -v python3.11 || command -v python3)
VENV ?= .venv
BIN := $(VENV)/bin
BACKEND := backend
FRONTEND := frontend
export PYTHONPATH := $(BACKEND)

.PHONY: setup dev test lint seed pipeline-once help

help:
	@echo "make setup          Create venv and install backend deps + pre-commit"
	@echo "make dev            Run API (uvicorn) and UI (vite) together"
	@echo "make test           Backend pytest (and frontend vitest if present)"
	@echo "make lint           Ruff check + format check"
	@echo "make seed           Sync YAML config into the database"
	@echo "make pipeline-once  Run one ingest/score/publish cycle"

setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r $(BACKEND)/requirements.txt
	$(BIN)/pre-commit install
	@echo "Setup complete. Copy .env.example to .env if you have not already."

# Starts the API. If frontend/package.json exists, also starts Vite.
dev:
	@echo "Starting API on http://127.0.0.1:8000 ..."
	@if [ -f $(FRONTEND)/package.json ]; then \
		echo "Starting UI on http://127.0.0.1:5173 ..."; \
		(cd $(BACKEND) && ../$(BIN)/uvicorn main:app --reload --host 127.0.0.1 --port 8000) & \
		(cd $(FRONTEND) && npm run dev); \
	else \
		echo "frontend/ not scaffolded yet — API only."; \
		cd $(BACKEND) && ../$(BIN)/uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	fi

test:
	cd $(BACKEND) && ../$(BIN)/pytest
	@if [ -f $(FRONTEND)/package.json ]; then \
		cd $(FRONTEND) && npm test; \
	fi

lint:
	cd $(BACKEND) && ../$(BIN)/ruff check .
	cd $(BACKEND) && ../$(BIN)/ruff format --check .

seed:
	cd $(BACKEND) && ../$(BIN)/python ../scripts/seed.py

pipeline-once:
	cd $(BACKEND) && ../$(BIN)/python -m pipeline.run
