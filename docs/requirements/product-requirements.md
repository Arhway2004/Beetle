# Product requirements (summary)

Source: the Beetle Keeper AI master brief plus the monorepo brief. This is the condensed, testable form.

## Users & platforms
A keeper of rhinoceros beetles (DHH, CCK, custom species). Android APK and iOS (iPhone 14 Pro Max).
Mac (M4, 24 GB) hosts optional local AI. Simplified Chinese default; English and Thai.

## Core (must work offline, without AI or backend)
1. Beetles with unique codes (`DHH-001`), species/custom species, sex, acquisition/hatch/estimated
   hatch ± uncertainty, life stage (L1/L2/L3 [+ early/middle/late label], prepupa, pupa, adult),
   status (active/deceased/transferred/archived), notes, photos, full event history.
2. Unlimited weight history; difference, % change, average daily/weekly change, historical max,
   multi-beetle comparison, filters (species/sex/stage); weight loss handled; growth not assumed linear.
3. Substrate changes (date, type, brand, batch, quantity, weight, condition, next planned date, photos)
   and container changes (previous/new volume) as history events.
4. Temperature: manual readings, multiple sensors, current/min/max, user target & thresholds, charts.
   Measured violations distinguished from AI predictions. No universal "ideal" temperature.
5. Stage never inferred from weight.
6. Reminders with states suggested/confirmed/scheduled/completed/cancelled/expired; only confirmed are
   scheduled; dedupe per beetle+event+period; accept/reject/edit date/edit message/postpone/disable similar;
   local notifications that work with the Mac offline; contextual permission; time zones, reboots, OS limits.
7. Backups: export all records + photos, versioned, integrity-checked, duplicate-safe restore.
8. Analytics: totals, by species, by stage, upcoming reminders, recent measurements, growth and
   comparison charts, temperature trends, substrate history, AI observation history. No causal claims.

## AI (optional)
9. Chat assistant that retrieves records through a controlled read-only tool layer before answering;
   calculations by deterministic code; answers distinguish verified/calculated/observation/hypothesis/
   recommendation/unknown; never fabricates.
10. Proactive care: deterministic triggers + AI interpretation returning schema-validated structured
    suggestions with evidence and confidence; never auto-scheduled.
11. Auditable AI memory: analyses, evidence, feedback, prediction outcomes; deletable without touching records.
12. Hybrid routing: Mac (Ollama, Qwen3-8B) / on-device (llama.cpp, Qwen3-1.7B) / deterministic engine;
    manual choice; capability-aware fallback; explicit "no model" state; no silent cloud use.
13. Vision: separate provider interface; unavailable until a real model is integrated and validated;
    never diagnoses from a single photo.

## Security & privacy
No account, no analytics, no hardcoded credentials, secure credential storage, authenticated and
encrypted gateway, explicit consent before data leaves the phone, read-only AI tools, Ollama never public.

## Repository
Single monorepo; components independently buildable/testable; REST + OpenAPI under `/api/v1`;
versioned migrations; secrets outside Git; path-filtered CI; sync designed but not faked.
