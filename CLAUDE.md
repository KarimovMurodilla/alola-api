# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Run locally
```bash
pip install -r requirements.txt
alembic revision --autogenerate -m "Initial"
alembic upgrade head
python src/main.py        # runs on localhost:8000
```

### Run with Docker
```bash
docker-compose up --build  # runs on 0.0.0.0:4765
```

### Tests
```bash
pytest -v tests/           # run all tests
pytest -v tests/test_auth.py  # run a single test file
```

## Architecture

This is a FastAPI app that acts as a proxy/adapter for the **Billz** retail platform API (`api-admin.billz.ai`). It exposes products and order data, with Redis caching in front of Billz API calls.

### Key patterns

**Unit of Work (`src/utils/unitofwork.py`):** All database operations go through `UnitOfWork`, which holds repository instances and manages the SQLAlchemy session lifecycle. Inject it into routes via `UOWDep` (`src/api/dependencies.py`).

**Repository (`src/utils/repository.py`):** `SQLAlchemyRepository` is the base class for all DB repositories. Each model gets a concrete subclass (e.g. `UsersRepository`). Models must implement `to_read_model()` for serialization.

**Billz Client (`src/utils/custom_client.py`):** `Client` is an async context manager wrapping `aiohttp`. It auto-authenticates against Billz on first use and stores the bearer token in Redis. On 401, it re-logs in and retries. Use it inside `BillzService` methods.

**Redis caching (`src/utils/cache/`):** Products are cached as a Redis list (`products` key, 300s TTL). The `/products` endpoint reads from Redis first; if the key is missing it fetches from Billz and populates the cache. A separate `count` key stores the total.

**Auth:** JWT via cookies using `fastapi-users`. Strategy lives in `src/auth/auth.py`. The `SECRET` env var is the signing key.

### Config (`src/config.py`)
Reads from `.env`. Required vars:
- `SECRET` — JWT signing key
- `BILLZ_SECRET_KEY`, `BILLZ_API_KEY` — Billz credentials
- `FRONTEND_BASE_URL`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`, `REDIS_USERNAME`, `REDIS_DATABASE`, `REDIS_TTL_STATE`, `REDIS_TTL_DATA`

Database is **SQLite** locally (`database.db`) and PostgreSQL in production — swap `DATABASE_URL` in `config.py`.

### Tests
`tests/conftest.py` overrides the DB session to use a separate `test.db` SQLite file and overrides `UnitOfWork.session_factory`. Tests use `pytest-asyncio` in auto mode (configured in `pyproject.toml`).
