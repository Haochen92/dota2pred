import os
import json
import aiohttp
from typing import Any
from dota_oracle_common.utils import load_workspace_env

load_workspace_env()

STEAM_URL = "http://api.steampowered.com/"
API_KEY: str | None = os.getenv("STEAM_API")

_session: aiohttp.ClientSession | None = None


def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession(headers={"Accept": "application/json"})
    return _session


async def fetch_steam_data(endpoint: str) -> dict[Any, Any] | None:
    if API_KEY is None:
        raise ValueError("STEAM_API environment variable is not set.")

    url = f"{STEAM_URL}{endpoint}"
    params: dict[str, str] = {"key": API_KEY, "format": "json"}

    session = _get_session()
    async with session.get(url, params=params) as response:
        if response.status != 200:
            raise ValueError(f"Request failed with status {response.status}")

        body_bytes = await response.read()
        if not body_bytes:
            raise ValueError("Empty response body from Steam API.")

        # Simple approach: let JSON parse bytes first; then minimal UTF-8 fallback
        try:
            return json.loads(body_bytes)
        except Exception:
            pass

        try:
            text = body_bytes.decode("utf-8", errors="replace")
            return json.loads(text)
        except Exception as e:
            ct = response.headers.get("Content-Type", "unknown")
            raise ValueError(f"Failed to decode or parse JSON from Steam API (Content-Type: {ct}): {e}")
