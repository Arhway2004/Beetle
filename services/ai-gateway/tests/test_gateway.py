from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from ai_gateway.config import Settings
from ai_gateway.main import create_app

TOKEN = "t" * 40
AUTH = {"Authorization": f"Bearer {TOKEN}"}
ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "packages/api-contracts/fixtures/suggestions"


class FakeOllama:
    """Records requests and replays canned /api/chat responses."""

    def __init__(self, chat_replies: list[dict[str, Any] | Exception] | None = None, models=("qwen3:8b",)):
        self.chat_replies = list(chat_replies or [])
        self.models = list(models)
        self.requests: list[dict[str, Any]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": m} for m in self.models]})
        if request.url.path == "/api/chat":
            body = json.loads(request.content)
            self.requests.append(body)
            reply = self.chat_replies.pop(0)
            if isinstance(reply, Exception):
                raise reply
            if "status" in reply:
                return httpx.Response(reply["status"], json={"error": "x"})
            return httpx.Response(200, json={"model": body["model"], "done_reason": "stop", **reply})
        return httpx.Response(404)


def make_client(fake: FakeOllama, **overrides) -> TestClient:
    settings = Settings(gateway_token=TOKEN, _env_file=None, **overrides)
    return TestClient(create_app(settings, ollama_transport=httpx.MockTransport(fake.handler)))


def msg(content: str = "", tool_calls: list | None = None) -> dict[str, Any]:
    return {"message": {"role": "assistant", "content": content, "tool_calls": tool_calls or []}}


# ------------------------------------------------------------------ security


def test_requires_bearer_token():
    c = make_client(FakeOllama())
    assert c.get("/api/v1/health").status_code == 401
    assert c.get("/api/v1/health", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert c.post("/api/v1/chat", json={"messages": [{"role": "user", "content": "hi"}]}).status_code == 401
    assert c.get("/api/v1/health", headers=AUTH).status_code == 200


def test_settings_reject_weak_token_and_remote_ollama():
    with pytest.raises(ValueError):
        Settings(gateway_token="short", _env_file=None)
    with pytest.raises(ValueError, match="localhost"):
        Settings(gateway_token=TOKEN, ollama_base_url="http://192.168.1.5:11434", _env_file=None)
    with pytest.raises(ValueError):
        Settings(gateway_token=TOKEN, gateway_tls_cert="cert.pem", _env_file=None)


def test_docs_disabled_by_default_and_body_limit():
    c = make_client(FakeOllama(), gateway_max_body_bytes=100)
    assert c.get("/docs").status_code == 404
    r = c.post("/api/v1/chat", headers=AUTH, json={"messages": [{"role": "user", "content": "x" * 500}]})
    assert r.status_code == 413


def test_rate_limit():
    c = make_client(FakeOllama(), gateway_rate_limit_per_minute=2)
    assert [c.get("/api/v1/capabilities", headers=AUTH).status_code for _ in range(3)] == [200, 200, 429]


def test_only_allowed_models():
    c = make_client(FakeOllama())
    r = c.post(
        "/api/v1/chat", headers=AUTH, json={"model": "other:70b", "messages": [{"role": "user", "content": "x"}]}
    )
    assert r.status_code == 400


# ------------------------------------------------------------------ health


def test_health_reports_models_and_degraded_states():
    assert make_client(FakeOllama()).get("/api/v1/health", headers=AUTH).json()["status"] == "ok"
    missing = make_client(FakeOllama(models=["llama3:8b"])).get("/api/v1/health", headers=AUTH).json()
    assert missing["status"] == "degraded" and missing["models"] == []

    def down(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    c = TestClient(
        create_app(Settings(gateway_token=TOKEN, _env_file=None), ollama_transport=httpx.MockTransport(down))
    )
    body = c.get("/api/v1/health", headers=AUTH).json()
    assert body == {"status": "degraded", "ollama_reachable": False, "models": [], "default_model": "qwen3:8b"}


def test_capabilities_do_not_claim_vision():
    caps = make_client(FakeOllama()).get("/api/v1/capabilities", headers=AUTH).json()
    assert caps["vision"] is False and caps["tool_calling"] is True


# ------------------------------------------------------------------ chat


def test_chat_relays_tools_and_returns_tool_calls_without_executing():
    fake = FakeOllama(
        [msg(tool_calls=[{"function": {"name": "get_growth_metrics", "arguments": {"beetle_id": "CCK-001"}}}])]
    )
    c = make_client(fake)
    tools = [{"type": "function", "function": {"name": "get_growth_metrics", "description": "d", "parameters": {}}}]
    r = c.post("/api/v1/chat", headers=AUTH, json={"messages": [{"role": "user", "content": "q"}], "tools": tools})
    assert r.status_code == 200
    call = r.json()["message"]["tool_calls"][0]
    assert call["name"] == "get_growth_metrics" and call["arguments"] == {"beetle_id": "CCK-001"} and call["id"]
    sent = fake.requests[0]
    assert (
        sent["stream"] is False
        and sent["think"] is False
        and sent["tools"][0]["function"]["name"] == "get_growth_metrics"
    )


def test_chat_converts_tool_messages_and_strips_thinking():
    fake = FakeOllama([msg("<think>secret reasoning</think>[CALCULATED] +4 g")])
    c = make_client(fake)
    r = c.post(
        "/api/v1/chat",
        headers=AUTH,
        json={
            "messages": [
                {"role": "user", "content": "q"},
                {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{"id": "a", "name": "list_beetles", "arguments": {}}],
                },
                {"role": "tool", "content": '{"beetles": []}', "tool_name": "list_beetles"},
            ]
        },
    )
    assert r.json()["message"]["content"] == "[CALCULATED] +4 g"
    sent = fake.requests[0]["messages"]
    assert sent[1]["tool_calls"] == [{"function": {"name": "list_beetles", "arguments": {}}}]
    assert sent[2] == {"role": "tool", "content": '{"beetles": []}', "tool_name": "list_beetles"}


def test_malformed_tool_calls_are_dropped():
    fake = FakeOllama(
        [
            msg(
                tool_calls=[
                    {"function": {"name": "rm -rf /", "arguments": {}}},
                    {"function": {"name": "list_beetles", "arguments": '{"status": "active"}'}},
                ]
            )
        ]
    )
    calls = make_client(fake).post("/api/v1/chat", headers=AUTH, json={"messages": [{"role": "user", "content": "q"}]})
    assert [c["name"] for c in calls.json()["message"]["tool_calls"]] == ["list_beetles"]
    assert calls.json()["message"]["tool_calls"][0]["arguments"] == {"status": "active"}


def test_chat_rejects_unknown_fields_and_maps_ollama_errors():
    c = make_client(FakeOllama([{"status": 404}, httpx.ReadTimeout("slow"), httpx.ConnectError("down")]))
    bad = c.post("/api/v1/chat", headers=AUTH, json={"messages": [{"role": "user", "content": "q", "x": 1}]})
    assert bad.status_code == 422
    body = {"messages": [{"role": "user", "content": "q"}]}
    assert c.post("/api/v1/chat", headers=AUTH, json=body).status_code == 503  # model not pulled
    assert c.post("/api/v1/chat", headers=AUTH, json=body).status_code == 504
    assert c.post("/api/v1/chat", headers=AUTH, json=body).status_code == 503


# ------------------------------------------------------------------ proactive


def _fixture(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


def test_interpret_returns_only_schema_valid_items_unchanged():
    good = _fixture("valid/possible-prepupa.json")
    bad = _fixture("invalid/no-confirmation.json")
    fake = FakeOllama([msg(json.dumps({"schema_version": "1", "suggestions": [good, bad]}))])
    r = make_client(fake).post("/api/v1/proactive/interpret", headers=AUTH, json={"context": {"beetle": {"id": "x"}}})
    assert r.status_code == 200
    assert r.json() == {"schema_version": "1", "suggestions": [good]}
    assert r.headers["X-Rejected-Suggestions"] == "1"
    assert fake.requests[0]["format"]["properties"]["suggestions"]["items"]["additionalProperties"] is False


def test_interpret_retries_once_on_non_json_then_fails():
    fake = FakeOllama([msg("not json"), msg("still not json")])
    r = make_client(fake).post("/api/v1/proactive/interpret", headers=AUTH, json={"context": {}})
    assert r.status_code == 502 and len(fake.requests) == 2


def test_interpret_invalid_envelope_yields_nothing():
    fake = FakeOllama([msg(json.dumps({"schema_version": "1", "suggestions": [], "auto_schedule": True}))])
    r = make_client(fake).post("/api/v1/proactive/interpret", headers=AUTH, json={"context": {}})
    assert r.json() == {"schema_version": "1", "suggestions": []} and r.headers["X-Rejected-Suggestions"] == "1"


# ------------------------------------------------------------------ contract


def test_routes_match_openapi_contract():
    spec = yaml.safe_load((ROOT / "packages/api-contracts/openapi/ai-gateway.v1.yaml").read_text())
    methods = {"get", "post", "put", "patch", "delete"}
    contract = {(p, m) for p, ops in spec["paths"].items() for m in ops if m in methods}
    generated = create_app(Settings(gateway_token=TOKEN, _env_file=None)).openapi()["paths"]
    implemented = {(p, m) for p, ops in generated.items() for m in ops if m in methods}
    assert implemented == contract
