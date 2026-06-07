from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """Runtime configuration for the API service."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Explicit CORS origins. `allow_origins=["*"]` combined with credentials is rejected by
    # browsers, so origins must be listed explicitly. Override per environment via the
    # CORS_ALLOWED_ORIGINS env var (comma-separated). Stored as a string so a plain
    # comma-separated env value is accepted (pydantic-settings JSON-decodes list fields).
    CORS_ALLOWED_ORIGINS: str = "https://dota.liuhaochen.com,http://localhost:3000"

    @property
    def cors_allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]


api_settings = APISettings()
