#!/usr/bin/env bash
# Starts a throwaway PostgreSQL without Docker (uses local initdb/pg_ctl, e.g.
# Homebrew). Data lives in .pgdata/ (git-ignored). Port 55432, user postgres, trust auth.
#   infra/scripts/dev-postgres.sh start|stop
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DATA="$ROOT/.pgdata"
case "${1:-start}" in
  start)
    [[ -d "$DATA" ]] || initdb -D "$DATA" -U postgres --auth=trust -E UTF8 >/dev/null
    pg_ctl -D "$DATA" -o "-p 55432 -k '' -c listen_addresses=127.0.0.1" -l "$DATA/server.log" start
    echo "TEST_DATABASE_ADMIN_URL=postgresql://postgres@127.0.0.1:55432/postgres"
    ;;
  stop) pg_ctl -D "$DATA" stop ;;
  *) echo "usage: $0 start|stop" >&2; exit 2 ;;
esac
