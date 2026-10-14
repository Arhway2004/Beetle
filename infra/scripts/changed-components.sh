#!/usr/bin/env bash
# Lists monorepo components touched between two refs (default: origin/main...HEAD).
# Mirrors the CI path filters so you can run only what changed: `make changed`.
# Portable to macOS bash 3.2 (no associative arrays).
set -euo pipefail
BASE="${1:-origin/main}"
FILES="$(git diff --name-only "$BASE"...HEAD 2>/dev/null || git diff --name-only HEAD)"
out=""
add() { case " $out " in *" $1 "*) ;; *) out="$out $1" ;; esac; }
while IFS= read -r f; do
  case "$f" in
    apps/mobile/*) add mobile ;;
    services/api/*) add api ;;
    services/ai-gateway/*) add gateway ;;
    database/*) add db; add api ;;
    packages/shared-types/*) add shared-types; add api; add gateway ;;
    packages/api-contracts/*) add contracts; add shared-types; add api; add gateway; add mobile ;;
  esac
done <<< "$FILES"
echo "${out# }"
