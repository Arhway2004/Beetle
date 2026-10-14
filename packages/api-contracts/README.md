# packages/api-contracts

Source of truth for interfaces between components.

* `openapi/api.v1.yaml` — backend API. `openapi/ai-gateway.v1.yaml` — Mac AI gateway.
* `schemas/ai-suggestion.v1.schema.json` (+ batch) — structured care suggestions. Strict:
  no extra fields, evidence required, `requires_user_confirmation` must be `true`.
* `fixtures/suggestions/{valid,invalid}` — vectors every validator (Dart, Python gateway, API) must agree on.
* `fixtures/growth/cases.json` — growth-metric vectors for the Dart and Python implementations.

`uv run pytest` validates the OpenAPI documents, the schemas, and the fixtures. After editing a schema,
run `packages/shared-types/generate.sh`.
