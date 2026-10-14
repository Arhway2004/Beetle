# Beetle Keeper monorepo — per-component commands.
# Each component also works on its own from its directory (see its README).
#
#   make help
#
SHELL := /bin/bash
.DEFAULT_GOAL := help

MOBILE   := apps/mobile
API      := services/api
GATEWAY  := services/ai-gateway
DB       := database
CONTRACT := packages/api-contracts
SHARED   := packages/shared-types
UV       := uv
PY       := --python 3.13
TEST_DATABASE_ADMIN_URL ?= postgresql://postgres@127.0.0.1:55432/postgres
export TEST_DATABASE_ADMIN_URL

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-20s\033[0m %s\n",$$1,$$2}'

# ---------------------------------------------------------------- all
.PHONY: test lint changed
test: contracts-test shared-test db-test api-test gateway-test mobile-test ## Run every component's tests
lint: contracts-lint shared-lint db-lint api-lint gateway-lint mobile-lint ## Lint every component
changed: ## List components changed vs origin/main
	@infra/scripts/changed-components.sh

# ---------------------------------------------------------------- mobile (Flutter)
.PHONY: mobile-get mobile-gen mobile-test mobile-lint mobile-run mobile-apk mobile-ios mobile-iphone
mobile-get: ## Fetch Flutter dependencies
	cd $(MOBILE) && flutter pub get
mobile-gen: ## Regenerate Drift code and localizations
	cd $(MOBILE) && dart run build_runner build && flutter gen-l10n
mobile-test: ## Flutter unit/widget/db tests
	cd $(MOBILE) && flutter test
mobile-lint: ## flutter analyze
	cd $(MOBILE) && flutter analyze
mobile-run: ## Run on a connected device/simulator
	cd $(MOBILE) && flutter run
mobile-apk: ## Build Android release APK
	cd $(MOBILE) && flutter build apk --release
mobile-ios: ## Build iOS (no codesign; signing needs an Apple team)
	cd $(MOBILE) && flutter build ios --release --no-codesign
mobile-iphone: ## Build release, install and launch on IPHONE=<devicectl id> (works when `flutter run` cannot install)
	@test -n "$(IPHONE)" || { echo "set IPHONE=<id from: xcrun devicectl list devices>"; exit 1; }
	cd $(MOBILE) && flutter build ios --release
	xcrun devicectl device install app --device $(IPHONE) $(MOBILE)/build/ios/iphoneos/Runner.app
	xcrun devicectl device process launch --terminate-existing --device $(IPHONE) com.beetlekeeper.beetleKeeper
mobile-schema: ## Snapshot Drift schema after bumping schemaVersion
	cd $(MOBILE) && dart run drift_dev make-migrations

# ---------------------------------------------------------------- contracts / shared types
.PHONY: contracts-test contracts-lint shared-gen shared-test shared-lint
contracts-test: ## Validate OpenAPI, JSON Schemas and fixtures
	cd $(CONTRACT) && $(UV) run $(PY) pytest -q
contracts-lint:
	cd $(CONTRACT) && $(UV) run $(PY) ruff check .
shared-gen: ## Regenerate Python models from JSON Schemas
	$(SHARED)/generate.sh
shared-test:
	cd $(SHARED) && $(UV) run $(PY) pytest -q
shared-lint:
	cd $(SHARED) && $(UV) run $(PY) ruff check .

# ---------------------------------------------------------------- database
.PHONY: db-pg-start db-pg-stop db-migrate db-seed db-check db-test db-lint
db-pg-start: ## Start a throwaway local PostgreSQL (no Docker) on :55432
	infra/scripts/dev-postgres.sh start
db-pg-stop:
	infra/scripts/dev-postgres.sh stop
db-migrate: ## Apply migrations to $$DATABASE_URL
	cd $(DB) && $(UV) run $(PY) python migrate.py
db-seed: ## Apply migrations + development seed data
	cd $(DB) && $(UV) run $(PY) python migrate.py --seed
db-check: ## Fail if migrations are pending or modified
	cd $(DB) && $(UV) run $(PY) python migrate.py --check
db-test: ## Migration tests (needs TEST_DATABASE_ADMIN_URL)
	cd $(DB) && $(UV) run $(PY) pytest -q
db-lint:
	cd $(DB) && $(UV) run $(PY) ruff check .

# ---------------------------------------------------------------- API
.PHONY: api-install api-test api-lint api-run
api-install:
	cd $(API) && $(UV) sync $(PY)
api-test: ## API tests (needs TEST_DATABASE_ADMIN_URL)
	cd $(API) && $(UV) run $(PY) pytest -q
api-lint:
	cd $(API) && $(UV) run $(PY) ruff check . && $(UV) run $(PY) ruff format --check .
api-run: ## Run the API locally (reads services/api/.env)
	cd $(API) && $(UV) run $(PY) uvicorn beetle_api.main:app --host 127.0.0.1 --port 8000 --reload

# ---------------------------------------------------------------- AI gateway (runs natively on the Mac)
.PHONY: gateway-install gateway-test gateway-lint gateway-run gateway-token gateway-cert ollama-pull
gateway-install:
	cd $(GATEWAY) && $(UV) sync $(PY)
gateway-test:
	cd $(GATEWAY) && $(UV) run $(PY) pytest -q
gateway-lint:
	cd $(GATEWAY) && $(UV) run $(PY) ruff check . && $(UV) run $(PY) ruff format --check .
gateway-run: ## Start the gateway (reads services/ai-gateway/.env)
	cd $(GATEWAY) && $(UV) run $(PY) beetle-ai-gateway
gateway-token: ## Generate a gateway access token
	@infra/scripts/gen-gateway-token.sh
gateway-cert: ## Generate a self-signed TLS cert and print its fingerprint
	infra/scripts/gen-tls-cert.sh
ollama-pull: ## Download the default model (~5 GB)
	ollama pull qwen3:8b

# ---------------------------------------------------------------- Docker stack (PostgreSQL + API)
.PHONY: up down logs
up: ## docker compose up (postgres, migrate, api)
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f api
