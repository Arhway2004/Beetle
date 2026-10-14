# services/api — Beetle Keeper API

FastAPI service under `/api/v1`: validation, business rules and PostgreSQL persistence.
The mobile app works without it; it is the server side for future synchronization (ADR 0004).
Contract: `packages/api-contracts/openapi/api.v1.yaml` (a test asserts routes match it).

```bash
uv sync --python 3.13
cp .env.example .env               # DATABASE_URL=postgresql+psycopg://…
python ../../database/migrate.py   # schema is owned by database/, never created by the API
uv run uvicorn beetle_api.main:app --reload
```
Or the whole stack: `make up` from the repo root (PostgreSQL + migrations + API in Docker).

| Endpoint | |
|---|---|
| `GET /api/v1/health` | DB reachability + applied schema version |
| `GET/POST /api/v1/species` | built-in + custom species |
| `GET/POST /api/v1/beetles`, `GET/PATCH/DELETE /api/v1/beetles/{id}` | PATCH needs `revision` (409 on mismatch); DELETE tombstones |
| `GET/POST /api/v1/beetles/{id}/weights`, `DELETE …/weights/{rid}` | append-only history |
| `GET /api/v1/beetles/{id}/growth-metrics?since_days=` | deterministic metrics (same vectors as the app) |
| `POST /api/v1/ai/suggestions/validate` | schema + evidence checks; creates nothing |

Tests need a PostgreSQL where they may create databases:
`TEST_DATABASE_ADMIN_URL=postgresql://postgres@127.0.0.1:55432/postgres uv run pytest`
(`make db-pg-start` starts one without Docker).
