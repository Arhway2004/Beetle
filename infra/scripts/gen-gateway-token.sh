#!/usr/bin/env bash
# Prints a new random gateway token. Put it in services/ai-gateway/.env as
# GATEWAY_TOKEN and enter it once in the app (Settings → Mac AI gateway).
set -euo pipefail
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
