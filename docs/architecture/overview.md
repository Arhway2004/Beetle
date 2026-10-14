# Architecture overview

## Components and boundaries

| Component | Owns | Talks to | Must never |
|---|---|---|---|
| `apps/mobile` | All breeding data (SQLite via Drift), rules engine, reminders, notifications, backups, AI tool execution | AI gateway (HTTPS), API (future sync) | Access a database server directly; depend on any server for core features |
| `services/ai-gateway` | Auth, transport security, Ollama relay, output validation | Ollama on `127.0.0.1` | Store or modify records; expose Ollama to the network |
| `services/api` | Server-side validation, business rules, persistence | PostgreSQL | Create or alter schema (migrations do that) |
| `database` | PostgreSQL schema & migrations | — | Edit applied migrations |
| `packages/api-contracts` | OpenAPI, JSON Schemas, test vectors | — | Contain implementation code |
| `packages/shared-types` | Generated Python models + strict validators | — | Be edited by hand (`generate.sh`) |

## Mobile app layers (`apps/mobile/lib`)

```
presentation/   screens & widgets (Dashboard, Beetles, Records, AI Assistant, Reminders, Analytics, Settings)
application/    use cases wiring repositories + domain + infrastructure; Riverpod providers
domain/         pure Dart: enums, growth metrics, care rules, reminder state machine & dedupe,
                suggestion validator, AI router / orchestrator / tools, vision interface
data/           Drift tables, database, repositories, read model for AI tools and rules
infrastructure/ notifications, Mac gateway client (TLS pinning), llama.cpp placeholder, secure storage,
                photo storage, backup/restore
core/           theme, router (GoRouter), formatting, ids
l10n/           ARB files: zh (default), en, th
```

Drift row classes are used as data entities directly; pure domain logic works on small value
types (`WeightPoint`, `BeetleCareSnapshot`, …) so it is testable without a database.

## Data model principles

* **Stable IDs**: UUID v4 primary keys generated on the device; human codes (`DHH-001`) are unique
  and never reused (tombstoned beetles keep their code).
* **History, not state**: weight, container, substrate and life-stage changes are append-only events.
  "Current" values are derived from the latest event, so deleting a record falls back to the previous one.
* **Tombstones**: `deleted_at` instead of hard deletes; `revision` increments on every edit.
* **Stage is never inferred** from weight — only set by explicit life-stage records.
* Timestamps are UTC instants; displayed in local time.

## AI design

```
user question
   │
AiOrchestrator (phone) ──AiRouter──▶ provider (Mac gateway │ on-device │ none)
   │   ▲                                   │
   │   └── tool_calls ◀────────────────────┘   model asks for data
   ▼
BreedingTools (read-only, deterministic) ── SQLite
   │ results (+ record ids as evidence)
   ▼
final answer with labelled lines → [VERIFIED] [CALCULATED] [OBSERVATION] [HYPOTHESIS] [RECOMMENDATION] [UNKNOWN]
   │
AI memory (ai_analyses + evidence_references, feedback, prediction outcome)
```

* Calculations: `get_growth_metrics` / `compare_growth` run Dart code; the model is told not to compute.
* The only non-read tool, `propose_reminder_draft`, stores nothing — it shows a draft the user can confirm.
* Routing: user picks auto / Mac / phone. Auto falls back to the phone **only** if it supports every
  required capability. If nothing qualifies, the UI says so; no answer is fabricated.
* Consent is required before the first transmission to the Mac and is reset when the gateway address
  changes. A non-private host (not LAN / Tailscale / localhost) triggers an extra warning.
* Vision: separate `VisionProvider`; this release ships only `UnavailableVisionProvider`.

## Proactive care

1. After every saved record, `CareRuleEngine` (deterministic) checks: significant weight change,
   measurement gap (larvae only — never prompts digging up a prepupa/pupa), substrate plan/interval,
   **measured** temperature threshold violations (user thresholds only), prepupa-related observations
   (always low confidence, "don't disturb"), user-configured emergence windows; stale reminders expire.
2. Optional AI interpretation (button, or auto setting) sends one beetle's records to the gateway,
   which returns schema-validated suggestions. The app re-validates and rejects suggestions for another
   beetle or citing record IDs not in the provided context. AI suggestions are always stored as
   `basis = ai_inference`.
3. Every result is a `suggested` reminder. Dedupe key = beetle + sensor + event + anchoring record;
   rejected suggestions are not re-proposed for the same period; "disable similar" adds a suppression.
4. Only `confirmed` reminders are handed to the OS (`scheduled`).

## Reminders & notifications

States: `suggested → confirmed → scheduled → completed`, plus `cancelled` / `expired`.
`ReminderScheduler.reconcile()` runs at launch, on resume and after every change: it keeps the soonest
60 reminders registered (iOS allows 64 pending), cancels stale OS notifications, falls back to inexact
alarms when Android exact-alarm permission is missing, and leaves reminders `confirmed` when permission
is denied. Permission is requested the first time the user confirms or creates a reminder. Scheduling is
by absolute instant (time-zone safe); Android reboots are covered by the plugin's boot receiver.

## Security

* Gateway: bearer token (≥ 32 chars, constant-time compare), TLS required for any non-loopback bind,
  Ollama must be on localhost, request size and rate limits, unknown fields rejected, docs off by default,
  no access logs (bodies contain breeding data).
* App: token in Keychain/Keystore (`flutter_secure_storage`), never in SQLite or backups; HTTPS required
  (Android cleartext disabled); self-signed certs accepted only when the SHA-256 fingerprint matches.
* Backups exclude provider settings and secrets.

See the ADRs in [adr/](adr/) for the reasoning behind these choices.
