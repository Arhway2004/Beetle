"""Minimal, dependency-light PostgreSQL migration runner.

Applies ``migrations/V<NNN>__<name>.sql`` in version order, each in its own
transaction, and records version + SHA-256 checksum in ``schema_migrations``.
Applied files must never change: a checksum mismatch aborts.

Usage:
    python migrate.py                 # apply pending migrations
    python migrate.py --check         # exit 1 if anything is pending or modified
    python migrate.py --seed          # also apply seeds/*.sql (development only)

Reads DATABASE_URL (SQLAlchemy-style ``postgresql+psycopg://`` is accepted).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg

HERE = Path(__file__).resolve().parent
MIGRATIONS_DIR = HERE / "migrations"
SEEDS_DIR = HERE / "seeds"
_NAME = re.compile(r"^V(\d{3,})__([a-z0-9_]+)\.sql$")
_LOCK_ID = 7_413_001  # advisory lock key: one runner at a time


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path

    @property
    def sql(self) -> str:
        return self.path.read_text(encoding="utf-8")

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.path.read_bytes()).hexdigest()


class MigrationError(RuntimeError):
    pass


def normalize_url(url: str) -> str:
    return re.sub(r"^postgresql\+\w+://", "postgresql://", url)


def discover(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    found: list[Migration] = []
    for p in sorted(directory.glob("*.sql")):
        m = _NAME.match(p.name)
        if not m:
            raise MigrationError(f"invalid migration file name: {p.name}")
        found.append(Migration(int(m.group(1)), m.group(2), p))
    versions = [m.version for m in found]
    if len(set(versions)) != len(versions):
        raise MigrationError("duplicate migration versions")
    return sorted(found, key=lambda m: m.version)


def _ensure_table(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version     INTEGER PRIMARY KEY,
            name        TEXT NOT NULL,
            checksum    CHAR(64) NOT NULL,
            applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def status(conn: psycopg.Connection, directory: Path = MIGRATIONS_DIR) -> tuple[list[Migration], list[str]]:
    """Returns (pending migrations, problems)."""
    _ensure_table(conn)
    applied = {v: c for v, c in conn.execute("SELECT version, checksum FROM schema_migrations")}
    migrations = discover(directory)
    known = {m.version for m in migrations}
    problems = [f"V{v:03d} applied in database but file is missing" for v in applied if v not in known]
    problems += [
        f"V{m.version:03d} ({m.name}) was modified after being applied"
        for m in migrations
        if m.version in applied and applied[m.version].strip() != m.checksum
    ]
    pending = [m for m in migrations if m.version not in applied]
    return pending, problems


def migrate(url: str, directory: Path = MIGRATIONS_DIR, seed: bool = False) -> list[int]:
    applied_now: list[int] = []
    with psycopg.connect(normalize_url(url), autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (_LOCK_ID,))
        try:
            pending, problems = status(conn, directory)
            if problems:
                raise MigrationError("; ".join(problems))
            for m in pending:
                with conn.transaction():
                    conn.execute(m.sql)
                    conn.execute(
                        "INSERT INTO schema_migrations (version, name, checksum) VALUES (%s, %s, %s)",
                        (m.version, m.name, m.checksum),
                    )
                applied_now.append(m.version)
            if seed:
                for p in sorted(SEEDS_DIR.glob("*.sql")):
                    with conn.transaction():
                        conn.execute(p.read_text(encoding="utf-8"))
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (_LOCK_ID,))
    return applied_now


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args(argv)
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2
    try:
        if args.check:
            with psycopg.connect(normalize_url(url), autocommit=True) as conn:
                pending, problems = status(conn)
            for p in problems:
                print(f"ERROR: {p}")
            for m in pending:
                print(f"pending: V{m.version:03d} {m.name}")
            return 1 if (pending or problems) else 0
        done = migrate(url, seed=args.seed)
        print(f"applied: {', '.join(f'V{v:03d}' for v in done) or 'nothing (up to date)'}")
        return 0
    except MigrationError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
