from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def is_loopback(host: str) -> bool:
    if host in ("localhost", "::1"):
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class Settings(BaseSettings):
    """Gateway configuration from environment variables (or a git-ignored .env)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    gateway_token: SecretStr = Field(..., description="Bearer token shared with the app (>= 32 chars)")
    gateway_host: str = "127.0.0.1"
    gateway_port: int = 8443
    gateway_tls_cert: str | None = None
    gateway_tls_key: str | None = None
    gateway_enable_docs: bool = False
    gateway_rate_limit_per_minute: int = 30
    gateway_max_body_bytes: int = 1_000_000
    gateway_allowed_models: list[str] = Field(default_factory=list)

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"
    ollama_timeout_seconds: float = 120
    ollama_allow_remote: bool = False

    @field_validator("gateway_token")
    @classmethod
    def _token_strength(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("GATEWAY_TOKEN must be at least 32 characters (use `make gateway-token`)")
        return v

    @model_validator(mode="after")
    def _security(self) -> Settings:
        host = urlparse(self.ollama_base_url).hostname or ""
        if not self.ollama_allow_remote and not is_loopback(host):
            raise ValueError("OLLAMA_BASE_URL must point to localhost; Ollama must never be exposed to the network")
        if bool(self.gateway_tls_cert) != bool(self.gateway_tls_key):
            raise ValueError("Set both GATEWAY_TLS_CERT and GATEWAY_TLS_KEY, or neither")
        return self

    @property
    def tls_enabled(self) -> bool:
        return bool(self.gateway_tls_cert and self.gateway_tls_key)

    @property
    def models(self) -> list[str]:
        return self.gateway_allowed_models or [self.ollama_model]
