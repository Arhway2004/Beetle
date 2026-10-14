# Beetle Keeper AI

Offline-first breeding management for rhinoceros beetles (e.g. *Dynastes hercules hercules* — DHH,
*Chalcosoma chiron kirbyi* — CCK), with an optional local AI assistant that runs on your own Mac.

One Git monorepo, strictly separated components:

```
beetle-keeper/
├─ apps/
│  ├─ mobile/            Flutter app (Android + iOS) — Drift/SQLite, offline-first   ← the product
│  └─ admin/             reserved for an optional web dashboard (not started)
├─ services/
│  ├─ api/               FastAPI backend /api/v1 — validation, business rules, PostgreSQL
│  └─ ai-gateway/        FastAPI gateway on the Mac → localhost Ollama (Qwen3-8B)
├─ packages/
│  ├─ api-contracts/     OpenAPI specs, JSON Schemas, shared test vectors
│  └─ shared-types/      Python models + validators generated from the contracts
├─ database/             PostgreSQL migrations (versioned SQL), runner, dev seeds, schema docs
├─ infra/                docker/ (compose overrides), scripts/ (tokens, TLS, local Postgres)
├─ docs/                 architecture, ADRs, requirements, API docs, status, release checklist
├─ docker-compose.yml    PostgreSQL + migrations + API
├─ Makefile              per-component commands (`make help`)
└─ .env.example          configuration template (real .env files are git-ignored)
```

```
 Flutter app (SQLite, offline) ──HTTPS + token──▶ AI Gateway (Mac) ──localhost──▶ Ollama
          │                                          (no DB access; returns tool-call requests,
          │                                           the app runs its own read-only tools)
          └──REST /api/v1 (future sync)──▶ API (FastAPI) ──▶ PostgreSQL (migrations in database/)
```

The app is fully usable with **no** backend and **no** AI: records, charts, reminders,
notifications and backups are all local.

## Quick start

| Goal | Commands |
|---|---|
| Run the app | `make mobile-get && make mobile-run` |
| Test the app | `make mobile-test` (`make mobile-lint` for the analyzer) |
| Android APK | `make mobile-apk` → `apps/mobile/build/app/outputs/flutter-apk/app-release.apk` |
| iOS build | `make mobile-ios` (unsigned); sign in Xcode for a device |
| Phone AI (experimental) | In the app: Settings → On-device AI → Download model (≈1.1 GB) → Enabled — see [docs/architecture/mobile-ai.md](docs/architecture/mobile-ai.md) |
| Mac AI | `make ollama-pull`, `make gateway-token`, `make gateway-cert`, then `make gateway-run` — see [services/ai-gateway](services/ai-gateway/README.md) |
| Backend stack | `cp .env.example .env` (set passwords) → `make up` |
| Backend tests without Docker | `make db-pg-start` then `make db-test api-test` |
| Everything | `make test`, `make lint`; `make changed` lists components touched vs `origin/main` |

Tool versions this repo is verified with: Flutter 3.38.10 / Dart 3.10.9, Xcode 16.2, Android SDK 35,
Python 3.13 via `uv`, PostgreSQL 14–16, Ollama 0.34.

## Rules of the architecture

* The frontend never talks to a database server; it only uses HTTP APIs.
* The backend owns business logic, validation and server-side persistence.
* The AI gateway cannot modify breeding records; AI output is a *suggestion*, schema-validated
  (gateway, app, and backend `/api/v1/ai/suggestions/validate`) and only scheduled after the user confirms.
* All numbers (growth, dates, thresholds) are computed by deterministic code, never by the model.
* No cloud dependency, no analytics, no account. Data leaves the phone only to your own Mac, after explicit consent.
* Migrations are versioned and append-only. Secrets stay out of Git.

More: [docs/architecture/overview.md](docs/architecture/overview.md) ·
[development status](docs/status.md) · [known limitations](docs/known-limitations.md) ·
[release checklist](docs/release-checklist.md).
