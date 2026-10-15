"""Environment settings and YAML config paths.

The API process should use `settings.database_url` (pooled).
Alembic and the pipeline should use `settings.database_url_direct`.
Never log these values.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Runtime settings loaded from process env and the repo-root `.env` file."""

    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(default="", description="Pooled Neon URL for the API")
    database_url_direct: str = Field(default="", description="Direct Neon URL for Alembic/pipeline")
    allowed_origins: str = "http://localhost:5173"
    environment: str = "development"
    log_level: str = "INFO"
    config_dir: str = ""

    @field_validator("database_url", "database_url_direct")
    @classmethod
    def _url_must_be_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("database URL is missing — set it in .env (value will not be logged)")
        return value.strip()

    @property
    def allowed_origin_list(self) -> list[str]:
        return [part.strip() for part in self.allowed_origins.split(",") if part.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings instance. Call `get_settings.cache_clear()` in tests."""
    return Settings()


def get_config_dir() -> Path:
    """YAML lives at repo-root /config. Override with CONFIG_DIR (absolute or relative to backend/)."""
    override = os.environ.get("CONFIG_DIR", "").strip()
    if override:
        path = Path(override)
        if not path.is_absolute():
            path = (BACKEND_DIR / path).resolve()
        return path
    return (BACKEND_DIR / "../config").resolve()


def sqlalchemy_url(raw_url: str) -> str:
    """psycopg3 needs the `postgresql+psycopg://` scheme."""
    if raw_url.startswith("postgresql+psycopg://"):
        return raw_url
    if raw_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw_url.removeprefix("postgresql://")
    return raw_url
