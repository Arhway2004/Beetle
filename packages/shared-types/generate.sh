#!/usr/bin/env bash
# Regenerates Python models and bundled schemas from packages/api-contracts.
# CI runs this and fails if the working tree changes (models out of date).
set -euo pipefail
cd "$(dirname "$0")"
SRC=../api-contracts/schemas
OUT=python/beetle_shared_types
cp "$SRC"/ai-suggestion.v1.schema.json "$SRC"/ai-suggestion-batch.v1.schema.json "$OUT/schemas/"
UV_HTTP_TIMEOUT=${UV_HTTP_TIMEOUT:-120} uvx --python 3.13 --from 'datamodel-code-generator==0.26.3' datamodel-codegen \
  --input "$SRC/ai-suggestion.v1.schema.json" --input-file-type jsonschema \
  --output-model-type pydantic_v2.BaseModel --use-annotated --field-constraints \
  --use-double-quotes --target-python-version 3.12 --disable-timestamp \
  --output "$OUT/ai_suggestion_v1.py"
echo "generated $OUT"
