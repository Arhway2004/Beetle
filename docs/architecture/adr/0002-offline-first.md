# ADR 0002 — Offline-first: the phone is the source of truth

**Status:** accepted

**Decision.** All core features (records, history, charts, rules, reminders, notifications, backup)
run on the device against SQLite (Drift). The backend and the Mac AI are optional enhancements and
their absence never blocks the UI. Reminders are scheduled locally, so they fire when the Mac is off.

**Consequences.** Server persistence requires a synchronization protocol (ADR 0004). Business rules
that matter offline (growth metrics, suggestion validation) exist in Dart *and* Python; they are kept
identical by shared test vectors in `packages/api-contracts/fixtures`.
