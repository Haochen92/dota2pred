import os
from typing import Any

import aiohttp

from dota_oracle_common.utils import load_workspace_env

from .aiohttp_client import aiohttp_session_provider


load_workspace_env()

STEAM_URL = "http://api.steampowered.com/"


class SteamClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str | None = None,
        base_url: str = STEAM_URL,
    ) -> None:
        self._session = session
        self._api_key = api_key or os.getenv("STEAM_API")
        self._base_url = base_url.rstrip("/") + "/"

    async def fetch_data(self, endpoint: str) -> dict[Any, Any] | None:
        if self._api_key is None:
            raise ValueError("STEAM_API environment variable is not set.")

        url = f"{self._base_url}{endpoint.lstrip('/')}"
        params = {"key": self._api_key, "format": "json"}

        async with self._session.get(url, params=params) as response:
            if response.status != 200:
                raise ValueError(f"Request failed with status {response.status}")

            body_bytes = await response.read()
            if not body_bytes:
                raise ValueError("Empty response body from Steam API.")

            try:
                json_data: dict[Any, Any] = await response.json(content_type=None)
                return json_data
            except (aiohttp.ContentTypeError, ValueError) as exc:
                content_type = response.headers.get("Content-Type", "unknown")
                raise ValueError(f"Failed to parse JSON from Steam API (Content-Type: {content_type}): {exc}") from exc


async def fetch_steam_data(endpoint: str) -> dict[Any, Any] | None:
    """Compatibility entry point for standalone callers; owns a short-lived session."""
    async with aiohttp_session_provider() as session:
        return await SteamClient(session=session).fetch_data(endpoint)
