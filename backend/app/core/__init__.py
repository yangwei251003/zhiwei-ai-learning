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
    cors_origins: str = ""
    rag_backend: str = "chroma"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "knowledge-uploads"

    # JWT
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # 可选补充模型
    deepseek_api_key: str = ""
    zhipu_api_key: str = ""
    zhipu_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    zhipu_model: str = "glm-4.7-flash"
    ant_bailing_api_key: str = ""
    ant_bailing_base_url: str = "https://api.ant-ling.com/v1"
    ant_bailing_model: str = "Ling-2.6-flash"
    agnes_api_key: str = ""
    agnes_base_url: str = "https://apihub.agnes-ai.com/v1"
    agnes_model: str = "agnes-2.0-flash"
    ollama_enabled: bool = False
    ollama_base_url: str = "http://127.0.0.1:11434/v1"
    ollama_model: str = "qwen2.5:3b"

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
        if self.rag_backend not in {"chroma", "supabase"}:
            raise ValueError("RAG_BACKEND must be chroma or supabase")
        if self.rag_backend == "supabase" and (
            not self.supabase_url.strip() or not self.supabase_service_role_key.strip()
        ):
            raise ValueError("Supabase RAG requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        return self

    @property
    def base_dir(self) -> Path:
        return Path(__file__).parent.parent.parent

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def uses_supabase_rag(self) -> bool:
        return self.rag_backend == "supabase"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
