# Development status

Verified on 2026-10-13 (macOS 15.6, Apple M4): Flutter 3.29.0, Xcode 16.2, Python 3.13 (uv), PostgreSQL 14.17, Ollama 0.34.1.

Legend: ✅ done & tested · 🟡 done, verified only partly · ⛔ blocked · ❌ not implemented

## Test results

| Component | Command | Result |
|---|---|---|
| apps/mobile | `flutter analyze` | no issues |
| apps/mobile | `flutter test` | **91 passed** (domain, repositories, Drift schema, proactive rules, reminders/scheduler, backup, gateway client, widget) |
| apps/mobile | `flutter test integration_test` | written, **not run** (needs a device/simulator session) |
| packages/api-contracts | `uv run pytest` | 25 passed (OpenAPI ×2 valid, schemas valid, fixtures) |
| packages/shared-types | `uv run pytest` | 21 passed |
| database | `uv run pytest` | 7 passed against PostgreSQL 14 |
| services/api | `uv run pytest` | 14 passed against PostgreSQL 14 (incl. contract-route equality) |
| services/ai-gateway | `uv run pytest` | 15 passed (Ollama mocked; incl. contract-route equality) |
| All Python | `ruff check` / `ruff format --check` | clean |
| Android | `flutter build apk --release --no-tree-shake-icons` | ✅ `app-release.apk` 68.3 MB (debug-signed: no keystore) |
| iOS | `flutter build ios --release --no-codesign` | ✅ `Runner.app` 29.5 MB (unsigned; built with `--no-tree-shake-icons`) |
| Gateway live | real process vs real Ollama (no model) | 401 without token; health `degraded`; chat → 503 "run ollama pull"; refuses LAN bind without TLS; HTTPS with self-signed cert works, fingerprint matches the app's pinning format |
| Docker stack | `docker compose up` | ⛔ not run — Docker daemon not running on this machine |
| GitHub Actions | workflows | written, ⛔ not run (no remote configured) |

## Features

| Feature | Status | Notes |
|---|---|---|
| Monorepo layout, per-component deps/tests/README | ✅ | |
| Beetle profiles (codes, species, custom species, sex, dates ± uncertainty, status, notes) | ✅ | |
| Life stages L1–adult + L3 early/mid/late label, never inferred from weight | ✅ | |
| Weight history, metrics, comparison, filters | ✅ | Dart and Python agree on shared vectors |
| Substrate / container history events | ✅ | |
| Temperature sensors, readings, thresholds, charts | ✅ | manual only; BLE/Wi-Fi ❌ |
| Photos (camera/gallery, per record) | 🟡 | storage & backup tested; camera/picker UI not exercised on a device |
| Unified records timeline, tombstone delete | ✅ | |
| Proactive rules → suggested reminders, dedupe, suppression, expiry | ✅ | |
| Reminder confirmation UI (accept/reject/edit/postpone/disable similar) | 🟡 | logic tested; sheet UI not widget-tested |
| Local notifications (schedule/cancel/reconcile, 64-cap, permission, inexact fallback) | 🟡 | scheduler logic tested with a fake; real OS delivery not verified on device |
| Backup export/restore (versioned, checksums, dedupe, conflicts) | ✅ | share/file-picker UI not exercised on device |
| Localization zh (default) / en / th | ✅ | en/th not reviewed by native speakers |
| Light/dark theme, responsive rail/bottom bar/drawer | ✅ | |
| AI router, consent, provider status | ✅ | |
| AI tool layer (read-only) + orchestrator loop + labelled answers | ✅ | with scripted provider |
| AI memory (analyses, evidence, feedback, outcomes, delete) | ✅ | |
| AI proactive interpretation (gateway + app validation, evidence check) | ✅ | with mocked model |
| Mac AI Gateway (auth, TLS, limits, Ollama relay) | 🟡 | ⛔ answers from Qwen3-8B not evaluated: model not downloaded (~5 GB; run `make ollama-pull`) |
| Backend API `/api/v1` + suggestion validation | ✅ | app does not call it yet (by design until sync) |
| PostgreSQL migrations + runner + seeds | ✅ | |
| Offline sync | ❌ | designed in ADR 0004; intentionally not faked |
| On-device AI (llama.cpp) | ❌ | reported as unavailable in-app; plan in architecture/mobile-ai.md |
| Vision AI | ❌ | `UnavailableVisionProvider`; marked unavailable in UI |
| Admin web | ❌ | placeholder README |
| Release signing | ⛔ | needs your Android keystore and Apple Developer team |

## Blockers needing you
1. `ollama pull qwen3:8b` (≈5 GB) to evaluate real AI answers.
2. Start Docker Desktop to run `make up` (PostgreSQL + API stack).
3. Android: create an upload keystore + `android/key.properties`. iOS: select a Team in Xcode.
4. `flutter precache --force` to repair the local Flutter cache (icon tree shaking).
5. Push to a GitHub remote to run CI.
