# infra

* `../docker-compose.yml` (repo root) — PostgreSQL 16 + one-shot migrations + API, bound to 127.0.0.1.
* `docker/docker-compose.test.yml` — disposable PostgreSQL on :55432 for tests.
* `scripts/gen-gateway-token.sh` — random gateway token.
* `scripts/gen-tls-cert.sh [host] [ip]` — self-signed cert in `infra/tls/` (git-ignored) + fingerprint.
* `scripts/dev-postgres.sh start|stop` — PostgreSQL without Docker (Homebrew `initdb`/`pg_ctl`).
* `scripts/changed-components.sh [base]` — components affected by a diff (mirrors CI path filters).

The Flutter app and the AI gateway are intentionally not containerized: the app runs on devices and
the gateway must run natively on the Mac next to Ollama (Metal acceleration).
