from pydantic_settings import BaseSettings, SettingsConfigDict


class Service_URL(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    BASE_INFERENCE_URL: str = "http://localhost:3333"
    BASE_FRONTEND_URL: str = ""  # Placeholder for frontend URL later

    # --- Polymarket odds capture (paper-betting feasibility; read-only, public endpoints) ---
    # Disabled by default: the stage stays inert until explicitly turned on, so it can ship
    # dormant while the match->market join is validated against live data. See
    # docs/2026-06-08-polymarket-odds-capture.md.
    ODDS_CAPTURE_ENABLED: bool = False
    BASE_GAMMA_URL: str = "https://gamma-api.polymarket.com"  # market discovery (no auth)
    BASE_CLOB_URL: str = "https://clob.polymarket.com"  # order books (no auth)
    # Dota events are discovered via Gamma's /events endpoint filtered by this tag slug (confirmed
    # against the live API -- it returns events whose markets carry per-game "Game N Winner"
    # child_moneyline markets). Configurable in case Polymarket re-slugs the tag.
    ODDS_DOTA_TAG_SLUG: str = "dota-2"

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
