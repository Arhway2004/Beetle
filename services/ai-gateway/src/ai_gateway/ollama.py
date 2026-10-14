"""Thin async client for the local Ollama HTTP API (/api/chat, /api/tags)."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

import httpx

from .schemas import ChatMessage, ToolCall, ToolDefinition

_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


class OllamaUnavailable(Exception):
    """Ollama is not running, or the requested model is not pulled."""


class OllamaTimeout(Exception):
    pass


class OllamaBadOutput(Exception):
    pass


def strip_thinking(text: str) -> str:
    return _THINK.sub("", text).strip()


def to_ollama_messages(messages: list[ChatMessage]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        msg: dict[str, Any] = {"role": m.role, "content": m.content}
        if m.tool_calls:
            msg["tool_calls"] = [{"function": {"name": t.name, "arguments": t.arguments}} for t in m.tool_calls]
        if m.role == "tool" and m.tool_name:
            msg["tool_name"] = m.tool_name
        out.append(msg)
    return out


def parse_tool_calls(raw: list[dict[str, Any]] | None) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for item in raw or []:
        fn = item.get("function") or {}
        args = fn.get("arguments") or {}
        if isinstance(args, str):  # some models return a JSON string
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                args = {}
        if not isinstance(args, dict):
            args = {}
        name = fn.get("name")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z_][a-z0-9_]*", name):
            continue  # drop malformed calls; the app only executes known tool names anyway
        calls.append(ToolCall(id=uuid.uuid4().hex[:12], name=name, arguments=args))
    return calls


class OllamaClient:
    def __init__(self, base_url: str, timeout: float, transport: httpx.AsyncBaseTransport | None = None):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(timeout, connect=5.0),
            transport=transport,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def models(self) -> list[str]:
        try:
            r = await self._client.get("/api/tags", timeout=5.0)
            r.raise_for_status()
        except (httpx.TransportError, httpx.HTTPStatusError) as e:
            raise OllamaUnavailable(str(e)) from e
        return [m.get("name", "") for m in r.json().get("models", [])]

    async def chat(
        self,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "options": {"temperature": 0.2},
        }
        if tools:
            body["tools"] = [t.model_dump() for t in tools]
        if response_format is not None:
            body["format"] = response_format
        try:
            r = await self._client.post("/api/chat", json=body)
        except httpx.TimeoutException as e:
            raise OllamaTimeout(str(e)) from e
        except httpx.TransportError as e:
            raise OllamaUnavailable(str(e)) from e
        if r.status_code == 404:
            raise OllamaUnavailable(f"model {model!r} is not available in Ollama (run `ollama pull {model}`)")
        if r.status_code >= 400:
            raise OllamaBadOutput(f"Ollama error {r.status_code}: {r.text[:300]}")
        data = r.json()
        if not isinstance(data, dict) or not isinstance(data.get("message"), dict):
            raise OllamaBadOutput("unexpected Ollama response shape")
        return data
