# services/ai-gateway — Mac AI Gateway

Authenticated HTTPS front for a **localhost-only** Ollama. Stateless; no database access; cannot
modify breeding records. Contract: `packages/api-contracts/openapi/ai-gateway.v1.yaml`.

## 1. Install Ollama and the model (Mac, Apple silicon)
```bash
brew install ollama          # or the app from ollama.com
ollama serve                 # keep the default bind 127.0.0.1:11434 — never 0.0.0.0
ollama pull qwen3:8b         # ≈5 GB; fits comfortably in 24 GB unified memory
```

## 2. Configure
```bash
cp .env.example .env
make -C ../.. gateway-token      # paste into GATEWAY_TOKEN
make -C ../.. gateway-cert       # writes infra/tls/, prints SHA-256 fingerprint for the app
```
`.env`:
```
GATEWAY_TOKEN=<token>
GATEWAY_HOST=0.0.0.0            # or a specific LAN/Tailscale IP; requires TLS
GATEWAY_PORT=8443
GATEWAY_TLS_CERT=../../infra/tls/gateway.crt
GATEWAY_TLS_KEY=../../infra/tls/gateway.key
OLLAMA_MODEL=qwen3:8b
```

## 3. Run
```bash
uv sync --python 3.13
uv run beetle-ai-gateway
```
The process refuses to bind a non-loopback address without TLS, and refuses an `OLLAMA_BASE_URL`
that is not localhost. For access away from home, use a VPN such as Tailscale; never port-forward.

## Endpoints (`Authorization: Bearer …`)
| | |
|---|---|
| `GET /api/v1/health` | Ollama reachability, allowed models present |
| `GET /api/v1/capabilities` | chat/tool calling/proactive: true; vision: false |
| `POST /api/v1/chat` | one model turn; returns text or tool-call requests (the app runs the tools) |
| `POST /api/v1/proactive/interpret` | schema-valid care suggestions only (`X-Rejected-Suggestions` header) |

Limits: 30 requests/min, 1 MB bodies, unknown JSON fields rejected, `/docs` disabled unless
`GATEWAY_ENABLE_DOCS=true`. Access logs are off because bodies contain breeding data.

## Tests
`uv run pytest` — Ollama is mocked (`httpx.MockTransport`); no model download needed.
