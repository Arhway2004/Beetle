# Plan: UI, growth roadmap, localization, sync foundations (2026-10)

Status: **proposal + Phase 1 in progress.** "Implemented" below means merged in the working tree;
everything else is a proposal. Findings are from **source review only** unless marked *(seen on
device)* — the app could not be run from the agent sandbox.

## 1. Audit

| # | Area | Finding | Evidence |
|---|---|---|---|
| A1 | Navigation | With Analytics/Settings open the bottom bar passes `selectedIndex: 0`, so Dashboard looks selected (only the indicator was hidden). **Fixed** — see Phase 1. | `presentation/shell/home_shell.dart` |
| A2 | Beetle detail | One long `ListView`: profile → lineage → record chips → growth chart → reminders → photos → full history → AI analyses. No roadmap; the record entry points are 6 equal-weight chips. | `presentation/beetles/beetle_detail_screen.dart` |
| A3 | Growth roadmap | Missing. Data needed exists: `life_stage_events(occurred_at, stage, l3_phase, is_estimated)`, `weight_records(measured_at, created_at)`. | `data/database/tables.dart` |
| A4 | Stages | Domain has `l1 l2 l3 prepupa pupa adult` — **no `egg`**. Server CHECK constraint matches. | `domain/models/enums.dart`, `V001__initial_schema.sql:164` |
| A5 | Errors | 10 places show raw exceptions (`showSnack(context, '$e')`), e.g. record/beetle/reminder forms, backup, AI settings, assistant. | `grep "'\$e'" lib/presentation` |
| A6 | Loading states | 23 `valueOrNull ?? const []` reads; on the detail page a loading or failed photo/weight/reminder query renders as "empty". | `beetle_detail_screen.dart:111-118` |
| A7 | Photos | Thumbnails delete on long-press only; no preview, no visible actions. | `beetle_detail_screen.dart:240` |
| A8 | Beetle list | Search + 4 filter menus; no "reset filters"; filtered-empty and truly-empty share one message. | `presentation/beetles/beetles_screen.dart` |
| A9 | Dashboard | Counts and species/stage chips first; today's care tasks are not first. | `presentation/dashboard/dashboard_screen.dart` |
| A10 | Language | zh/en/th selector persists an explicit code; no "use device language"; unknown codes fall back to zh. Strings not reviewed by native speakers. | `application/providers.dart:79-85` |
| A11 | Forms | Inputs survive a failed save (controllers kept); Save button is disabled while `_saving` in beetle form; record/reminder forms need checking. | form screens |
| A12 | Sync | ADR 0004 is accurate: sync columns exist (UUIDs, `revision`, tombstones, server `change_seq`); **no outbox, no sync state, no auth**. | `adr/0004-offline-sync.md` |
| A13 | Privacy doc / UI | Privacy text says data stays on device; true today. Must change when sync/training exist. | `l10n/*.arb: privacyBody` |

## 2. UI recommendations, ranked by user impact

1. **Beetle detail restructure** (A2, A3): header + roadmap first, one primary *Add record* button with
   *Weight* and *Stage* quick actions, then tabs **Overview · Records · Photos**.
2. **Readable errors and real loading/empty/retry states** (A5, A6).
3. **Dashboard: today first** (A9): due/overdue reminders and suggested reminders, quick record, then
   collection summary.
4. **Navigation consistency** (A1) — done.
5. **Photos: tap to preview, visible ⋯ menu** (A7).
6. **Beetle list: reset filters, distinct "no match" state** (A8).
7. **Language: "Use device language"**, Thai/Chinese wrapping and 200 % text checks (A10).

## 3. Proposed beetle detail layout (phone)

```
┌ AppBar: DHH-001                         ✎  ⋯ ┐
│ [photo/icon]  DHH-001 · ♂ · Active            │
│               D. h. hercules                  │
│               L3 (late) · 32.5 g · 12 Oct     │
│ ┌ Growth roadmap ───────────────────────────┐ │
│ │ ● L1   Not recorded                       │ │
│ │ ● L2   3 Jan → 1 Feb · 2 weights          │ │
│ │ ◉ L3   since 1 Feb (current) · 4 weights  │ │  tap a stage → its records & photos
│ │ ○ Prepupa  Upcoming                        │ │
│ └───────────────────────────────────────────┘ │
│ [ + Add record ]  [⚖ Weight] [⇄ Stage]        │
│ ─ Overview │ Records │ Photos ─               │
│ Overview: growth chart, reminders, parents,   │
│           facts, AI analyses (collapsed)      │
│ Records: unified history, filter by type      │
│ Photos: grid, tap = preview, ⋯ = actions      │
└───────────────────────────────────────────────┘
```
Each roadmap row states its status in **text** (current / recorded / not recorded / upcoming), not
only by icon or colour, and carries a semantics label for screen readers.

## 4. Roadmap rules (implemented: `domain/growth/growth_roadmap.dart`)

* Events ordered by `occurred_at`, then `created_at`, then `id`; **current stage = last event**
  (identical to the repository's SQL).
* Consecutive same-stage events form one *period* (keeps L3 early/mid/late labels inside it).
* A period ends at the **next record**, which is shown as such — never as a confirmed completion.
* Weight → period whose `[start, end)` contains `measured_at`; a weight exactly at a transition
  belongs to the new period; weights before the first stage event are listed as
  "before first recorded stage" and not attributed.
* Stages before the current one without events: **Not recorded** (no dates invented). After it:
  **Upcoming** (no prediction). `is_estimated` events are labelled *approx.*
* Backdated records sort by observation time. A stage earlier than one already recorded
  (e.g. pupa → L3) is kept, flagged *needs review*, never reordered or dropped.
* Deletions are tombstones; the roadmap is derived from live rows, so it falls back automatically.

## 5. Target code structure and dependency direction

```
presentation ──▶ application ──▶ domain ◀── data / infrastructure
   widgets        use cases,       pure Dart     Drift repos, notifications,
   UI state       Riverpod         rules, value  files, HTTP, (future) sync
                  providers        types         transport
```
* `domain/` imports nothing from Flutter, Riverpod, Drift, HTTP or plugins (already true; keep it).
* Proposed module split inside existing layers (incremental, no rewrite):
  `domain/{beetles, records, growth, care, media, ai, sync}`;
  `application/{beetles, records, care, sync}` instead of one 200-line `providers.dart`.
* Sync (Phase 2): `domain/sync/` (outbox entry, sync state, conflict types — pure),
  `data/sync/outbox_repository.dart` (Drift), `infrastructure/sync/sync_transport.dart` (interface;
  HTTP impl only after a provider is chosen).

## 6. Phases

| Phase | Scope | State |
|---|---|---|
| 1 | Roadmap domain + tests; nav fix; detail page restructure with roadmap widget and Add record flow; localized errors; loading/empty/retry; photo preview/actions; filter reset; dashboard ordering; "use device language"; l10n audit | **started**: roadmap domain + tests, nav fix + widget test |
| 2 | Split providers by module; Drift `sync_outbox` written in the same transaction as each change; sync state model (local only / pending / syncing / synced / needs attention) shown read-only; conflict table per ADR 0004; photo hash manifest | proposal |
| 3 | Verify current free-tier docs/pricing for 3–4 options compatible with FastAPI + PostgreSQL; pick one; write push/pull/auth contracts in `packages/api-contracts`; separate consent for sync vs. training in privacy docs | proposal |
| 4 | Real cloud integration after provider choice | not started |

## 7. Open decisions (defaults used unless you object)

| Decision | Default |
|---|---|
| Add an `egg` stage? Needs enum + Drift (text, no migration) + server V003 CHECK change + contracts. | **Yes**, additive and backward compatible. Waiting for confirmation before touching the server schema. |
| Detail grouping | Tabs Overview / Records / Photos under a fixed header + roadmap. |
| Thai calendar | Gregorian dates formatted with `th` locale; Buddhist-era display (พ.ศ.) as an option later. Stored values stay UTC instants. |
| Notification text after language change | Re-render pending notifications on the next `reconcile()` (launch/resume). |
| Training data | Out of scope until sync exists; separate opt-in, documented in Phase 3. |
