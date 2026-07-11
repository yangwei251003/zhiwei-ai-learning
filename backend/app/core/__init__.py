from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import os
from pathlib import Path


class Settings(BaseSettings):
    # 讯飞星火
    spark_app_id: str = ""
    spark_api_key: str = ""
    spark_api_secret: str = ""

    # 数据库
    database_url: str = "sqlite:///./a3_learning.db"

    # 向量库
    vector_db_path: str = "./chroma_db"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    knowledge_upload_dir: str = "./knowledge_uploads"

    # JWT
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # 可选补充模型
    deepseek_api_key: str = ""

    log_level: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def require_secret_key(self) -> "Settings":
        if not self.secret_key.strip():
            raise ValueError("SECRET_KEY must be configured before startup")
        return self

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent.parent


@lru_cache()
def get_settings() -> Settings:
    return Settings()
