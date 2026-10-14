# ADR 0004 — Offline synchronization (designed, not implemented)

**Status:** proposed. No sync endpoint or UI exists; nothing pretends to sync.

**Foundations already in place**
* Client-generated UUID primary keys on both sides; built-in species share fixed UUIDs.
* `created_at`, `updated_at`, `deleted_at` (tombstones), `revision` on every syncable table (SQLite and PostgreSQL).
* Server `change_seq` (global sequence, bumped by trigger on every insert/update) for incremental pulls.
* API `PATCH` uses optimistic concurrency (`revision` → `409 Conflict`).

**Planned protocol**
1. `POST /api/v1/sync/push` — client sends rows changed since its last push
   (`{table, id, revision, base_revision, row}`); server applies when `base_revision` matches.
2. Conflicts (base revision mismatch) are **not** auto-resolved for profile fields: the server returns
   both versions, the app stores a `sync_conflicts` row and asks the user. Append-only history rows
   (weights, observations, …) cannot conflict except on tombstones; a tombstone wins over an older edit.
3. `GET /api/v1/sync/pull?after=<change_seq>` — server returns rows (including tombstones) with
   higher `change_seq`; the client stores the high-water mark.
4. Beetle-code collisions (two devices both created `DHH-003`) are reported as conflicts; the user renames one.
5. Photos sync separately by content hash.
6. Authentication: device-bound tokens; sync stays opt-in with explicit consent.

**Open questions:** multi-user households, server-side reminders (likely never — reminders stay device-local).
