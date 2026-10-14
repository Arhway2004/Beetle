"""Migration tests against a real PostgreSQL.

Set TEST_DATABASE_ADMIN_URL to a server where the test may create and drop
databases (default: postgresql://postgres@127.0.0.1:5432/postgres). Each test
gets a fresh, uniquely named database.
"""

from __future__ import annotations

import os
import shutil
import sys
import uuid
from pathlib import Path

import psycopg
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import migrate  # noqa: E402

ADMIN_URL = os.environ.get("TEST_DATABASE_ADMIN_URL", "postgresql://postgres@127.0.0.1:5432/postgres")


@pytest.fixture
def db_url():
    name = f"bk_test_{uuid.uuid4().hex[:10]}"
    try:
        admin = psycopg.connect(ADMIN_URL, autocommit=True)
    except psycopg.OperationalError as e:  # pragma: no cover - environment dependent
        pytest.skip(f"PostgreSQL not reachable at TEST_DATABASE_ADMIN_URL: {e}")
    admin.execute(f'CREATE DATABASE "{name}"')
    base = ADMIN_URL.rsplit("/", 1)[0]
    yield f"{base}/{name}"
    admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    admin.close()


def test_applies_all_and_is_idempotent(db_url):
    first = migrate.migrate(db_url)
    assert first == [m.version for m in migrate.discover()]
    assert migrate.migrate(db_url) == []
    with psycopg.connect(db_url) as conn:
        pending, problems = migrate.status(conn)
        assert pending == [] and problems == []
        tables = {r[0] for r in conn.execute("SELECT tablename FROM pg_tables WHERE schemaname='public'")}
    assert {"species", "beetles", "weight_records", "reminders", "evidence_references", "schema_migrations"} <= tables


def test_modified_migration_is_detected(db_url, tmp_path: Path):
    copy = tmp_path / "migrations"
    shutil.copytree(migrate.MIGRATIONS_DIR, copy)
    migrate.migrate(db_url, directory=copy)
    target = sorted(copy.glob("*.sql"))[0]
    target.write_text(target.read_text() + "\n-- edited\n")
    with pytest.raises(migrate.MigrationError, match="modified"):
        migrate.migrate(db_url, directory=copy)


def test_bad_file_names_are_rejected(tmp_path: Path):
    (tmp_path / "001_init.sql").write_text("SELECT 1;")
    with pytest.raises(migrate.MigrationError):
        migrate.discover(tmp_path)


def test_failed_migration_rolls_back(db_url, tmp_path: Path):
    copy = tmp_path / "migrations"
    shutil.copytree(migrate.MIGRATIONS_DIR, copy)
    (copy / "V999__broken.sql").write_text("CREATE TABLE half_done (id int); SELECT * FROM does_not_exist;")
    with pytest.raises(psycopg.errors.UndefinedTable):
        migrate.migrate(db_url, directory=copy)
    with psycopg.connect(db_url) as conn:
        assert conn.execute("SELECT to_regclass('half_done')").fetchone()[0] is None
        assert conn.execute("SELECT count(*) FROM schema_migrations WHERE version = 999").fetchone()[0] == 0


def test_schema_constraints_and_sync_columns(db_url):
    migrate.migrate(db_url, seed=True)
    with psycopg.connect(db_url) as conn:
        beetle = conn.execute("SELECT id, revision, change_seq FROM beetles WHERE code = 'DHH-901'").fetchone()
        assert beetle is not None
        conn.execute("UPDATE beetles SET notes = 'x' WHERE id = %s", (beetle[0],))
        rev, seq = conn.execute("SELECT revision, change_seq FROM beetles WHERE id = %s", (beetle[0],)).fetchone()
        assert rev == beetle[1] + 1 and seq > beetle[2]
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            conn.execute(
                "INSERT INTO weight_records (id, beetle_id, measured_at, weight_grams) VALUES (%s, %s, now(), 10)",
                (uuid.uuid4(), uuid.uuid4()),
            )
    with psycopg.connect(db_url) as conn, pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO weight_records (id, beetle_id, measured_at, weight_grams) VALUES (%s, %s, now(), 0)",
            (uuid.uuid4(), beetle[0]),
        )
    with psycopg.connect(db_url) as conn, pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO beetles (id, code, species_id) VALUES (%s, 'bad code', %s)",
            (uuid.uuid4(), "5c1d6b0e-0d1a-4c7e-9a00-000000000001"),
        )


def test_reminder_dedupe_key_unique_among_live_rows(db_url):
    migrate.migrate(db_url)
    sql = (
        "INSERT INTO reminders (id, event_type, title, due_at, status, source, dedupe_key, deleted_at)"
        " VALUES (%s, 'weight_loss', 't', now(), 'suggested', 'rule', 'k', %s)"
    )
    with psycopg.connect(db_url, autocommit=True) as conn:
        conn.execute(sql, (uuid.uuid4(), "2026-01-01"))  # tombstoned: does not block
        conn.execute(sql, (uuid.uuid4(), None))
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute(sql, (uuid.uuid4(), None))


def test_builtin_species_ids_match_mobile_app():
    app_db = Path(__file__).resolve().parents[2] / "apps/mobile/lib/data/database/app_database.dart"
    sql = (migrate.MIGRATIONS_DIR / "V001__initial_schema.sql").read_text()
    for code, uid in [("DHH", "5c1d6b0e-0d1a-4c7e-9a00-000000000001"), ("CCK", "5c1d6b0e-0d1a-4c7e-9a00-000000000002")]:
        assert f"'{code}': '{uid}'" in app_db.read_text()
        assert f"('{uid}', '{code}'" in sql
