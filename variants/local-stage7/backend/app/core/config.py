from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "小智析析"
    api_prefix: str = "/api"
    spark_api_key: str
    spark_api_password: str | None = None
    spark_app_id: str | None = None
    spark_api_secret: str | None = None
    spark_base_url: str = "https://spark-api-open.xf-yun.com/v1/chat/completions"
    spark_timeout_seconds: float = Field(default=180, ge=10, le=300)
    model_high: str = "generalv3.5"
    model_med: str = "generalv3"
    model_low: str = "lite"
    database_url: str = "sqlite:///./a3_learning.db"
    auto_create_tables: bool = False
    faiss_index_path: Path = Path("data/faiss/index.faiss")
    knowledge_upload_dir: Path = Path("data/knowledge")
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_dimension: int = Field(default=512, gt=0)
    retrieval_score_threshold: float = Field(default=0.35, ge=0, le=1)
    max_upload_mb: int = Field(default=20, gt=0, le=100)
    secret_key: str = Field(min_length=32)
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=1440, gt=0)
    cors_allowed_origins: str = "http://localhost:5173"
    log_level: str = "INFO"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @field_validator("spark_api_key")
    @classmethod
    def reject_empty_api_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("SPARK_API_KEY must not be empty")
        return value.strip()

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @property
    def spark_bearer_token(self) -> str:
        """Return the OpenAI-compatible credential, falling back for legacy env files."""
        return (
            self.spark_api_password.strip()
            if self.spark_api_password and self.spark_api_password.strip()
            else self.spark_api_key
        )

    def model_for(self, level: Literal["high", "medium", "low"] | str) -> str:
        models = {
            "high": self.model_high,
            "medium": self.model_med,
            "low": self.model_low,
        }
        try:
            configured = models[level]
        except KeyError as exc:
            raise ValueError(f"Unknown model level: {level}") from exc
        aliases = {
            "spark4.0": "generalv3.5",
            "spark3.5": "generalv3",
            "sparklite": "lite",
            "spark-max": "generalv3.5",
            "spark-pro": "generalv3",
            "spark-lite": "lite",
        }
        return aliases.get(configured.lower(), configured)


@lru_cache
def get_settings() -> Settings:
    return Settings()
