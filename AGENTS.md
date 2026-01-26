# AGENTS

Quick project-specific guidance for coding agents.

## Frontend
- This repo uses Turborepo. Run the frontend through Turborepo, not directly.
- Inside `apps/`, use `pnpm` for all frontend commands.

Example commands:
- From repo root: `pnpm dlx turbo dev`
- From `apps/web`: `pnpm run dev`

# Web
- This is main frontend project.
- Firstly exports `export NEXT_PUBLIC_BASE_URL=http://127.0.0.1:8000` to use backend.
- Then run `pnpm run dev` to start the frontend.

## Python
- Use `uv` for Python workflows.
- The only Python subproject is `python/backend`.

Example commands:
- From `python/backend`: `uv run pytest`
- From `python/backend`: `uv run python -m src.main`

## Backend

# Python Backend
- Use `uv` for Python workflows.
- The only Python subproject is `python/backend`.

Running tests:
Example command: `uv run pytest -s -v tests/`

Running the server:
Set database url via `export DATABASE_URL="postgresql://myuser:myuser@localhost:5432/experiment_tracker` - Use as is (This database set up for development purposes).
Example command: `uv run uvicorn api.main:app --reload --port 8000 --log-level debug`
