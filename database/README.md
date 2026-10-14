# database — PostgreSQL schema & migrations

* `migrations/V<NNN>__<name>.sql` — append-only, applied in order, each in a transaction.
  Never edit an applied file (checksums are verified; CI rejects modifications in PRs).
* `migrate.py` — runner (`schema_migrations` table, SHA-256 checksums, advisory lock).
* `seeds/` — development-only data (`--seed`), marked `[dev seed]`.
* `schema/` — documentation and ERD.

```bash
uv sync --python 3.13
DATABASE_URL=postgresql://… uv run python migrate.py          # apply
DATABASE_URL=postgresql://… uv run python migrate.py --check  # CI / deploy gate
TEST_DATABASE_ADMIN_URL=postgresql://postgres@127.0.0.1:55432/postgres uv run pytest
```
The phone uses its own SQLite schema (Drift, `apps/mobile/lib/data/database/tables.dart`); both
share column semantics and the built-in species UUIDs (tested).
