from pydantic_settings import BaseSettings


class Service_URL(BaseSettings):
    # model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    BASE_INFERENCE_URL: str = "http://localhost:3333"
    PUBLIC_MATCHES_INFERENCE_URL: str = f"{BASE_INFERENCE_URL}/predict/public"
    PUBLIC_MATCHES_METADATA_URL: str = f"{BASE_INFERENCE_URL}/metadata/public"
    PRO_MATCHES_INFERENCE_URL: str = f"{BASE_INFERENCE_URL}/predict/pro"
    PRO_MATCHES_METADATA_URL: str = f"{BASE_INFERENCE_URL}/metadata/pro"

    # Frontend Url
    BASE_FRONTEND_URL: str = ""  # Placeholder for frontend URL later
    PUBLIC_MATCHES_FRONTEND_URL: str = "f{BASE_FRONTEND_URL}/public_matches"


service_url = Service_URL()
