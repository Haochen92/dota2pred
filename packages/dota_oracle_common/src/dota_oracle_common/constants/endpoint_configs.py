from pydantic_settings import BaseSettings, SettingsConfigDict


class Service_URL(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    BASE_INFERENCE_URL: str = "http://localhost:3333"
    BASE_FRONTEND_URL: str = ""  # Placeholder for frontend URL later

    @property
    def PUBLIC_MATCHES_INFERENCE_URL(self) -> str:
        return f"{self.BASE_INFERENCE_URL}/predict/public"

    @property
    def PUBLIC_MATCHES_METADATA_URL(self) -> str:
        return f"{self.BASE_INFERENCE_URL}/metadata/public"

    @property
    def PRO_MATCHES_INFERENCE_URL(self) -> str:
        return f"{self.BASE_INFERENCE_URL}/predict/pro"

    @property
    def PRO_MATCHES_METADATA_URL(self) -> str:
        return f"{self.BASE_INFERENCE_URL}/metadata/pro"

    @property
    def PUBLIC_MATCHES_FRONTEND_URL(self) -> str:
        return f"{self.BASE_FRONTEND_URL}/public_matches"


service_url = Service_URL()
