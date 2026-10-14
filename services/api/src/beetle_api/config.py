from __future__ import annotations

import re

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://beetle:change-me@localhost:5432/beetle_keeper"
    api_cors_origins: str = ""

    @property
    def sqlalchemy_url(self) -> str:
        # Accept plain postgresql:// URLs too; always use the psycopg 3 driver.
        return re.sub(r"^postgresql(\+\w+)?://", "postgresql+psycopg://", self.database_url)

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]
