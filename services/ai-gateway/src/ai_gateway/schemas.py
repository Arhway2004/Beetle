"""Request/response models. See packages/api-contracts/openapi/ai-gateway.v1.yaml."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolCall(Strict):
    id: str = Field(default="", max_length=64)
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z_][a-z0-9_]*$")
    arguments: dict[str, Any] = Field(default_factory=dict)


class ChatMessage(Strict):
    role: Literal["system", "user", "assistant", "tool"]
    content: str = Field(default="", max_length=60_000)
    tool_calls: list[ToolCall] = Field(default_factory=list, max_length=10)
    tool_name: str | None = Field(default=None, max_length=64)


class ToolFunction(Strict):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z_][a-z0-9_]*$")
    description: str = Field(default="", max_length=2000)
    parameters: dict[str, Any] = Field(default_factory=dict)


class ToolDefinition(Strict):
    type: Literal["function"] = "function"
    function: ToolFunction


class ChatRequest(Strict):
    model: str | None = Field(default=None, max_length=100)
    messages: list[ChatMessage] = Field(min_length=1, max_length=80)
    tools: list[ToolDefinition] = Field(default_factory=list, max_length=24)


class AssistantMessage(Strict):
    role: Literal["assistant"] = "assistant"
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)


class ChatResponse(Strict):
    model: str
    message: AssistantMessage
    done_reason: str | None = None


class InterpretRequest(Strict):
    model: str | None = Field(default=None, max_length=100)
    context: dict[str, Any]


class HealthResponse(Strict):
    status: Literal["ok", "degraded"]
    ollama_reachable: bool
    models: list[str]
    default_model: str


class Capabilities(Strict):
    chat: bool
    tool_calling: bool
    proactive_interpretation: bool
    vision: bool
    default_model: str
    allowed_models: list[str]
