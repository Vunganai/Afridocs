"""
Application configuration via pydantic-settings.
All settings are loaded from environment variables / .env file.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production", "testing"] = "development"
    app_secret_key: str = "change-me"
    log_level: str = "INFO"

    # ── Supabase ─────────────────────────────────────────────
    supabase_url: str = "https://placeholder.supabase.co"
    supabase_anon_key: str = "placeholder-anon-key"
    supabase_service_role_key: str = "placeholder-service-role-key"
    supabase_jwt_secret: str = "placeholder-jwt-secret"

    # ── Database ─────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/afridocs"

    # ── Redis ─────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Celery ───────────────────────────────────────────────
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # ── Azure AI Document Intelligence ───────────────────────
    azure_document_intelligence_endpoint: str = "https://placeholder.cognitiveservices.azure.com/"
    azure_document_intelligence_key: str = "placeholder-key"

    # ── Azure OpenAI ─────────────────────────────────────────
    azure_openai_endpoint: str = "https://placeholder.openai.azure.com/"
    azure_openai_key: str = "placeholder-key"
    azure_openai_deployment_name: str = "gpt-4o"
    azure_openai_api_version: str = "2024-02-01"

    # ── Azure Blob Storage ────────────────────────────────────
    azure_storage_account_name: str = "placeholder"
    azure_storage_account_key: str = "placeholder-key"
    azure_storage_container_name: str = "afridocs-documents"

    # ── File Uploads ─────────────────────────────────────────
    max_upload_size_mb: int = 20
    allowed_mime_types: str = "application/pdf,image/jpeg,image/png,image/tiff"

    # ── CORS ─────────────────────────────────────────────────
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── AI Thresholds ─────────────────────────────────────────
    extraction_confidence_threshold: float = 0.80
    auto_approve_confidence_threshold: float = 0.95

    @property
    def allowed_mime_types_list(self) -> list[str]:
        return [m.strip() for m in self.allowed_mime_types.split(",")]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
