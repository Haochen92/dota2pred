import os
import json
import aiohttp
import chardet
from typing import Any
from dota_oracle_common.utils import load_workspace_env

load_workspace_env()

STEAM_URL = "http://api.steampowered.com/"
API_KEY: str | None = os.getenv("STEAM_API")


async def fetch_steam_data(endpoint: str) -> dict[Any, Any] | None:
    if API_KEY is None:
        raise ValueError("STEAM_API environment variable is not set.")

    url = f"{STEAM_URL}{endpoint}"
    params: dict[str, str] = {"key": API_KEY, "format": "json"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise ValueError(f"Request failed with status {response.status}")

            body_bytes = await response.read()
            if not body_bytes:
                raise ValueError("Empty response body from Steam API.")

            try:
                # Detect encoding and decode accordingly
                detection = chardet.detect(body_bytes)
                encoding = detection.get("encoding")

                if not encoding:
                    raise ValueError("Could not detect character encoding.")

                text = body_bytes.decode(encoding)
                return json.loads(text)
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                ct = response.headers.get("Content-Type", "unknown")
                raise ValueError(f"Failed to decode or parse JSON from Steam API (Content-Type: {ct}): {e}")
