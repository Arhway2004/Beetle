# ADR 0005 — Versioned backup archive

**Status:** accepted

**Decision.** Backups are ZIP files: `manifest.json` (format, `format_version`, `backup_id`,
`schema_version`, SHA-256 of `data.json` and every photo), `data.json` (raw rows of every exported
table, including tombstones), `photos/…`. Restore validates format, versions (refuses archives from a
newer schema), and every checksum before touching the database, rejects unsafe paths, detects code
conflicts (same `DHH-001`, different ID) and aborts without changes, then merges by primary key in
one transaction — inserting new rows and updating only when the backup row has a newer `updated_at`.
`backup_imports` records restored `backup_id`s to report duplicate imports.
Provider settings, consent and secrets are never exported.
