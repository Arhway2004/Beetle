# packages/shared-types

Python package `beetle_shared_types`, generated from `packages/api-contracts/schemas` by
`./generate.sh` (datamodel-code-generator; do not edit `ai_suggestion_v1.py`). Used by
`services/api` and `services/ai-gateway` as a uv path dependency.

The generated models are less strict than the schema, so always validate with
`validate_suggestion()` / `validate_batch()`, which check the raw JSON against the bundled JSON Schema
first. Dart does not use generated code: `apps/mobile/lib/domain/ai/care_suggestion.dart` is a
hand-written strict validator kept in line by the shared fixtures.
