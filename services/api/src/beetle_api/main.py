"""Beetle Keeper API (``/api/v1``).

Owns business rules, validation and server-side persistence. The mobile app is
offline-first and fully functional without this service; the API is the
foundation for future synchronization (see docs/architecture/adr/0004-sync.md).
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .config import Settings
from .db import Database
from .models import Health
from .routers import ai, records


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="Beetle Keeper API", version="1.0.0")
    app.state.db = Database(settings.sqlalchemy_url)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
        )

    @app.get("/api/v1/health", response_model=Health, tags=["health"])
    def health() -> Health:
        try:
            with app.state.db.engine.connect() as conn:
                version = conn.execute(text("SELECT max(version) FROM schema_migrations")).scalar()
            return Health(status="ok", database=True, schema_version=version)
        except Exception:  # noqa: BLE001 - report, do not crash
            return Health(status="degraded", database=False, schema_version=None)

    app.include_router(records.router)
    app.include_router(ai.router)
    return app


app = create_app()
