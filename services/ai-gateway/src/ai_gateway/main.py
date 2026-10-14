"""Beetle Keeper AI Gateway.

The only network-facing component on the Mac. It authenticates the app,
relays chat requests to a localhost-only Ollama, and validates structured
proactive-care output. It has no database access and cannot create, modify
or delete breeding records: tool calls requested by the model are returned to
the app, which executes its own read-only tools.
"""

from __future__ import annotations

import hmac
import json
import logging
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from importlib import resources
from typing import Any

import httpx
from beetle_shared_types import SuggestionValidationError, validate_batch, validate_suggestion
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import Settings
from .ollama import (
    OllamaBadOutput,
    OllamaClient,
    OllamaTimeout,
    OllamaUnavailable,
    parse_tool_calls,
    strip_thinking,
    to_ollama_messages,
)
from .prompts import PROACTIVE_SYSTEM_PROMPT
from .schemas import (
    AssistantMessage,
    Capabilities,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    InterpretRequest,
)

log = logging.getLogger("ai_gateway")
_bearer = HTTPBearer(auto_error=False)


def _suggestion_format_schema() -> dict[str, Any]:
    """Self-contained batch schema passed to Ollama's structured output."""
    pkg = resources.files("beetle_shared_types").joinpath("schemas")
    item = json.loads(pkg.joinpath("ai-suggestion.v1.schema.json").read_text(encoding="utf-8"))
    for k in ("$schema", "$id", "title", "description"):
        item.pop(k, None)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_version", "suggestions"],
        "properties": {
            "schema_version": {"type": "string", "enum": ["1"]},
            "suggestions": {"type": "array", "maxItems": 10, "items": item},
        },
    }


class RateLimiter:
    """Sliding one-minute window per client address (single-user gateway)."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= self.per_minute:
            return False
        q.append(now)
        return True


def create_app(settings: Settings, ollama_transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    ollama = OllamaClient(settings.ollama_base_url, settings.ollama_timeout_seconds, transport=ollama_transport)
    limiter = RateLimiter(settings.gateway_rate_limit_per_minute)
    format_schema = _suggestion_format_schema()
    expected_token = settings.gateway_token.get_secret_value().encode()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await ollama.close()

    app = FastAPI(
        title="Beetle Keeper AI Gateway",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.gateway_enable_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.gateway_enable_docs else None,
    )
    app.state.settings = settings

    @app.middleware("http")
    async def limits(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and int(length) > settings.gateway_max_body_bytes:
            return JSONResponse({"detail": "request too large"}, status_code=413)
        client = request.client.host if request.client else "unknown"
        if request.url.path.startswith("/api/") and not limiter.check(client):
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
        return await call_next(request)

    def require_token(creds: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> None:
        if (
            creds is None
            or creds.scheme.lower() != "bearer"
            or not hmac.compare_digest(creds.credentials.encode(), expected_token)
        ):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "invalid or missing token", headers={"WWW-Authenticate": "Bearer"}
            )

    def resolve_model(requested: str | None) -> str:
        model = requested or settings.ollama_model
        if model not in settings.models:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"model {model!r} is not allowed by this gateway")
        return model

    def map_errors(e: Exception) -> HTTPException:
        if isinstance(e, OllamaUnavailable):
            return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"Ollama unavailable: {e}")
        if isinstance(e, OllamaTimeout):
            return HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "Ollama timed out")
        return HTTPException(status.HTTP_502_BAD_GATEWAY, f"bad response from model: {e}")

    @app.get("/healthz", include_in_schema=False)
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/health", response_model=HealthResponse, dependencies=[Depends(require_token)])
    async def health() -> HealthResponse:
        try:
            models = await ollama.models()
            reachable = True
        except OllamaUnavailable:
            models, reachable = [], False
        return HealthResponse(
            status="ok" if reachable and settings.ollama_model in models else "degraded",
            ollama_reachable=reachable,
            models=[m for m in models if m in settings.models],
            default_model=settings.ollama_model,
        )

    @app.get("/api/v1/capabilities", response_model=Capabilities, dependencies=[Depends(require_token)])
    async def capabilities() -> Capabilities:
        return Capabilities(
            chat=True,
            tool_calling=True,
            proactive_interpretation=True,
            vision=False,  # no validated multimodal model is wired in
            default_model=settings.ollama_model,
            allowed_models=settings.models,
        )

    @app.post("/api/v1/chat", response_model=ChatResponse, dependencies=[Depends(require_token)])
    async def chat(req: ChatRequest) -> ChatResponse:
        model = resolve_model(req.model)
        try:
            data = await ollama.chat(model, to_ollama_messages(req.messages), tools=req.tools)
        except (OllamaUnavailable, OllamaTimeout, OllamaBadOutput) as e:
            raise map_errors(e) from e
        msg = data["message"]
        return ChatResponse(
            model=data.get("model", model),
            message=AssistantMessage(
                content=strip_thinking(msg.get("content") or ""),
                tool_calls=parse_tool_calls(msg.get("tool_calls")),
            ),
            done_reason=data.get("done_reason"),
        )

    @app.post("/api/v1/proactive/interpret", dependencies=[Depends(require_token)])
    async def interpret(req: InterpretRequest, response: Response) -> dict[str, Any]:
        """Returns only schema-valid suggestions. Invalid items are dropped and
        counted in ``X-Rejected-Suggestions``; nothing is ever repaired or acted on."""
        model = resolve_model(req.model)
        context = json.dumps(req.context, ensure_ascii=False, default=str)
        if len(context) > 200_000:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "context too large")
        messages = [
            {"role": "system", "content": PROACTIVE_SYSTEM_PROMPT},
            {"role": "user", "content": f"Breeding records (JSON):\n{context}"},
        ]
        last_error = ""
        for _attempt in range(2):
            try:
                data = await ollama.chat(model, messages, response_format=format_schema)
            except (OllamaUnavailable, OllamaTimeout, OllamaBadOutput) as e:
                raise map_errors(e) from e
            raw = strip_thinking(data["message"].get("content") or "")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as e:
                last_error = f"model output is not JSON: {e}"
                continue
            _, errors = validate_batch(parsed)
            if any(not e.startswith("suggestions/") for e in errors):  # envelope invalid
                response.headers["X-Rejected-Suggestions"] = "1"
                log.info("model output envelope invalid")
                return {"schema_version": "1", "suggestions": []}
            # Return the original items that pass the schema, unchanged (never repaired).
            valid: list[dict[str, Any]] = []
            for item in parsed["suggestions"]:
                try:
                    validate_suggestion(item)
                    valid.append(item)
                except SuggestionValidationError:
                    pass
            rejected = len(parsed["suggestions"]) - len(valid)
            response.headers["X-Rejected-Suggestions"] = str(rejected)
            if rejected:
                log.info("dropped %d invalid suggestion(s)", rejected)
            return {"schema_version": "1", "suggestions": valid}
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"model did not return valid JSON: {last_error}")

    return app
