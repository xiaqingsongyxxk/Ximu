# AGENTS.md

## Repository Structure

Monorepo with two main packages:
- `frontend/` - React 19 + Vite + TypeScript + TailwindCSS
- `backend/` - FastAPI + Python 3.13+

## Running Commands

### Frontend
```bash
cd frontend
npm run dev      # dev server
npm run build    # tsc -b && vite build
npm run lint    # eslint
```

### Backend
```bash
cd backend
uv run python main.py   # run server (uses uv, not python directly)
uv run ruff check     # lint
uv run ruff format    # format
```

## Key Conventions

- **Backend Python**: Use `uv run` for all commands (not bare `python`)
- **Backend lint**: Run `ruff check` then `ruff format` after edits
- **Docstrings**: Google style in Python code
- **Frontend path alias**: `@/` maps to `frontend/src`

## Architecture Notes

### Backend Structure
- `backend/apps/` - Feature modules (resume, parser, export, etc.)
- `backend/shared/` - Shared utilities (database, API clients, types)
- `backend/main.py` - FastAPI entrypoint with lifespan management
- Database: SQLite with async SQLAlchemy (aiosqlite)
- PDF generation: Playwright browser automation (auto-installs Chromium)
- LLM integration: Supports OpenAI and Anthropic providers
- Task system: In-memory task state with SSE streaming

### Frontend Structure
- `frontend/src/pages/` - Route components (Dashboard, EditorPage, etc.)
- `frontend/src/components/` - Reusable UI components
- `frontend/src/stores/` - Zustand state management
- `frontend/src/lib/api.ts` - Axios API client (baseURL: localhost:8000)
- State management: Zustand for global state
- Data fetching: React Query for server state
- Routing: React Router v7

### Important Patterns
- Backend routers are in `backend/apps/<feature>/router.py`
- Backend schemas are in `backend/apps/<feature>/schemas.py`
- Backend services are in `backend/apps/<feature>/service.py`
- Frontend API calls are centralized in `frontend/src/lib/api.ts`
- Frontend stores are in `frontend/src/stores/`

## Environment Setup

- Backend requires Python 3.13+
- Frontend requires Node.js
- Backend auto-installs Playwright Chromium on first run
- Database file: `backend/app.db` (SQLite)
- CORS is configured to allow all origins (development mode)

## Testing & Quality

- Backend: Run `uv run ruff check` and `uv run ruff format` after changes
- Frontend: Run `npm run lint` to check for issues
- No test framework configured yet

## Common Pitfalls

- Don't use bare `python` commands - always use `uv run`
- Backend uses async/await throughout - ensure proper async patterns
- Frontend API calls expect backend running on localhost:8000
- Playwright browser installation happens automatically on first backend start
