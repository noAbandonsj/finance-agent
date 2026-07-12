# Repository Guidelines

## Project Structure & Module Organization

The FastAPI backend lives in `backend/src/ai_finance/`, organized by responsibility: `api/`, `market/`, `analytics/`, `ai/`, `research/`, and `records/`. Backend tests mirror those areas under `backend/tests/`. Database migrations are in `backend/alembic/versions/`.

The Vue 3/TypeScript client is in `frontend/src/`. Put screens in `views/`, reusable UI in `components/`, Pinia state in `stores/`, and HTTP contracts in `api/`. Unit tests are in `frontend/tests/`; Playwright scenarios are in `frontend/e2e/`. Design notes belong in `docs/`, helper commands in `scripts/`, and local SQLite files in `data/`.

## Build, Test, and Development Commands

- `uv sync --all-packages --all-extras`: install backend and development dependencies.
- `cd frontend; npm install`: install the locked frontend dependencies.
- `.\scripts\dev.ps1`: apply Alembic migrations, start the API on port 8000, and run Vite on port 5173.
- `.\scripts\check.ps1`: run Ruff, Pytest, Vitest, the frontend build, and Playwright.
- `uv run --project backend pytest backend/tests/api/test_market_api.py`: run one backend test module.
- `cd frontend; npm test -- --run`: run frontend unit tests once.

Install Chromium once with `cd frontend; npx playwright install chromium` before running end-to-end checks.

## Coding Style & Naming Conventions

Use four-space indentation and type hints in Python. Ruff enforces a 100-character line limit and Python 3.13 compatibility. Use `snake_case` for Python functions/modules and `PascalCase` for classes and Pydantic models.

Follow existing Vue conventions: two-space indentation, `<script setup lang="ts">`, `PascalCase.vue` component names, and `camelCase` variables/functions. Keep API response types explicit in `frontend/src/api/types.ts`.

## Testing Guidelines

Pytest discovers `test_*.py`; Vitest uses `*.spec.ts`. Add tests to the corresponding domain suite and cover success, validation, and failure paths. Default backend runs exclude tests marked `live`. Run external-service tests explicitly with `pytest -m live` only when valid credentials are configured. No fixed coverage threshold exists, but changed behavior should have regression coverage.

## Commit & Pull Request Guidelines

History follows Conventional Commit prefixes such as `feat:` and `fix:`. Write short, imperative subjects (for example, `fix: preserve research evidence ordering`). Keep commits focused.

Pull requests should summarize user-visible behavior, list verification commands, link relevant issues or design documents, and include screenshots for UI changes. Note migrations, configuration changes, external API use, and any tests intentionally skipped.

## Security & Configuration

Copy `.env.example` to `.env`; never commit secrets or funded API keys. Preserve the read-only financial scope: do not add order execution or fund-transfer behavior without an explicit architecture and security review.
