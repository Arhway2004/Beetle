# Server schema (V001)

```mermaid
erDiagram
  species ||--o{ beetles : "species_id"
  temperature_sensors ||--o{ beetles : "sensor_id (optional)"
  temperature_sensors ||--o{ temperature_records : ""
  beetles ||--o{ weight_records : ""
  beetles ||--o{ observation_records : ""
  beetles ||--o{ substrate_changes : ""
  beetles ||--o{ container_changes : ""
  beetles ||--o{ life_stage_events : ""
  beetles ||--o{ ai_analyses : "optional"
  beetles ||--o{ reminders : "optional"
  ai_analyses ||--o{ reminders : "analysis_id"
  ai_analyses ||--o{ evidence_references : "cascade"
  reminders ||--o{ evidence_references : "cascade"
```

Every table: `id UUID PK`, `created_at`, `updated_at`, `deleted_at` (tombstone), `revision`,
`change_seq` (sync cursor). Trigger `touch_row()` maintains `updated_at`, `revision`, `change_seq`.

Device-only tables (not on the server): `photo_attachments` (files stay on the phone until photo sync
exists), `suggestion_suppressions`, `ai_provider_settings`, `app_settings`, `backup_imports`.

Notable constraints: beetle code `^[A-Z][A-Z0-9]{1,7}-[0-9]{3,6}$`; weight `0 < g < 1000`;
`l3_phase` only with stage `l3`; reminder status/source/basis enums; at most one live reminder per
`dedupe_key`.
