"""Each test gets a fresh PostgreSQL database migrated with database/migrate.py.

Set TEST_DATABASE_ADMIN_URL (default postgresql://postgres@127.0.0.1:5432/postgres).
"""

from __future__ import annotations

import importlib.util
import os
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from beetle_api.config import Settings
from beetle_api.main import create_app

ROOT = Path(__file__).resolve().parents[3]
ADMIN_URL = os.environ.get("TEST_DATABASE_ADMIN_URL", "postgresql://postgres@127.0.0.1:5432/postgres")

_spec = importlib.util.spec_from_file_location("migrate", ROOT / "database" / "migrate.py")
migrate = importlib.util.module_from_spec(_spec)
sys.modules["migrate"] = migrate
_spec.loader.exec_module(migrate)

DHH = "5c1d6b0e-0d1a-4c7e-9a00-000000000001"
CCK = "5c1d6b0e-0d1a-4c7e-9a00-000000000002"


@pytest.fixture
def db_url():
    name = f"bk_api_{uuid.uuid4().hex[:10]}"
    try:
        admin = psycopg.connect(ADMIN_URL, autocommit=True)
    except psycopg.OperationalError as e:  # pragma: no cover
        pytest.skip(f"PostgreSQL not reachable: {e}")
    admin.execute(f'CREATE DATABASE "{name}"')
    url = f"{ADMIN_URL.rsplit('/', 1)[0]}/{name}"
    migrate.migrate(url)
    yield url
    admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    admin.close()


@pytest.fixture
def client(db_url):
    app = create_app(Settings(database_url=db_url, _env_file=None))
    with TestClient(app) as c:
        yield c
    app.state.db.engine.dispose()
