import aiohttp
import os
from dota_oracle_common.utils import get_logger, load_workspace_env
from typing import Optional, Dict, Any
from datetime import timedelta

from prefect import task
from prefect.cache_policies import TASK_SOURCE, INPUTS

logger = get_logger(__name__)
load_workspace_env()

API_KEY = os.getenv("OPENDOTA_API")
BASE_URL = "https://api.opendota.com"
BASE_PATH = "/api/"

_FREE_TIMEOUT = aiohttp.ClientTimeout(total=120)
_PAID_TIMEOUT = aiohttp.ClientTimeout(total=60)

_session: aiohttp.ClientSession | None = None


def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


async def fetch_opendota(endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
    endpoint = endpoint.lstrip("/")
    url = f"{BASE_URL}{BASE_PATH}{endpoint}"
    session = _get_session()
    try:
        async with session.get(url, params=params, timeout=_FREE_TIMEOUT) as res:
            res.raise_for_status()
            json_data: dict[Any, Any] = await res.json()
            return json_data

    except (aiohttp.ClientConnectionError, aiohttp.ClientError, aiohttp.http.HttpProcessingError, ValueError) as e:
        error_message = f"{type(e).__name__}: {str(e)}"
        logger.error(error_message)
        raise


@task(
    retries=3,
    retry_delay_seconds=5,
    cache_policy=TASK_SOURCE + INPUTS,
    cache_expiration=timedelta(days=1),
)
async def fetch_opendota_api(endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
    """Fetch data from OpenDota API using paid API key. Cached for 1 day."""
    if not API_KEY:
        raise ValueError("Missing API KEY, unable to fetch data")

    endpoint = endpoint.lstrip("/")
    url = f"{BASE_URL}{BASE_PATH}{endpoint}"

    final_params = params.copy() if params else {}
    final_params["api_key"] = API_KEY

    session = _get_session()
    try:
        async with session.get(url, params=final_params, timeout=_PAID_TIMEOUT) as res:
            res.raise_for_status()
            json_data: dict[Any, Any] = await res.json()
            return json_data

    except (aiohttp.ClientConnectionError, aiohttp.ClientError, aiohttp.http.HttpProcessingError, ValueError) as e:
        error_message = f"{type(e).__name__}: {str(e)}"
        logger.error(error_message)
        raise


@task(
    retries=4,
    retry_delay_seconds=15,
)
async def fetch_opendota_api_uncached(endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
    """Paid OpenDota API call without Prefect task caching."""
    if not API_KEY:
        raise ValueError("Missing API KEY, unable to fetch data")

    endpoint = endpoint.lstrip("/")
    url = f"{BASE_URL}{BASE_PATH}{endpoint}"

    final_params = params.copy() if params else {}
    final_params["api_key"] = API_KEY

    session = _get_session()
    try:
        async with session.get(url, params=final_params, timeout=_PAID_TIMEOUT) as res:
            res.raise_for_status()
            json_data: dict[Any, Any] = await res.json()
            return json_data
    except (aiohttp.ClientConnectionError, aiohttp.ClientError, aiohttp.http.HttpProcessingError, ValueError) as e:
        error_message = f"{type(e).__name__}: {str(e)}"
        logger.error(error_message)
        raise
