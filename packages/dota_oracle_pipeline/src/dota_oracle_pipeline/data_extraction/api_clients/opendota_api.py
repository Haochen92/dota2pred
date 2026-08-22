import os
from datetime import timedelta
from typing import Any, Dict, Optional

import aiohttp
from prefect import task
from prefect.cache_policies import INPUTS, TASK_SOURCE

from dota_oracle_common.utils import get_logger, load_workspace_env

from .aiohttp_client import aiohttp_session_provider


logger = get_logger(__name__)
load_workspace_env()

BASE_URL = "https://api.opendota.com"
BASE_PATH = "/api/"

_FREE_TIMEOUT = aiohttp.ClientTimeout(total=120)
_PAID_TIMEOUT = aiohttp.ClientTimeout(total=60)


def retry_if_not_404(task, task_run, state) -> bool:
    """Retry transient errors but not a terminal OpenDota 404."""
    try:
        state.result(raise_on_failure=True)
    except aiohttp.ClientResponseError as exc:
        return exc.status != 404
    except Exception:
        return True
    return False


class OpenDotaClient:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_key: str | None = None,
        base_url: str = BASE_URL,
    ) -> None:
        self._session = session
        self._api_key = api_key or os.getenv("OPENDOTA_API")
        self._base_url = base_url.rstrip("/")

    def _url(self, endpoint: str) -> str:
        return f"{self._base_url}{BASE_PATH}{endpoint.lstrip('/')}"

    async def fetch_free(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
        try:
            async with self._session.get(self._url(endpoint), params=params, timeout=_FREE_TIMEOUT) as response:
                response.raise_for_status()
                json_data: dict[Any, Any] = await response.json()
                return json_data
        except aiohttp.ClientResponseError as exc:
            if exc.status not in (404, 429):
                logger.error(f"{type(exc).__name__}: {exc}")
            raise
        except (aiohttp.ClientConnectionError, aiohttp.ClientError, ValueError) as exc:
            logger.error(f"{type(exc).__name__}: {exc}")
            raise

    async def fetch_paid(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
        if not self._api_key:
            raise ValueError("Missing API KEY, unable to fetch data")

        final_params = params.copy() if params else {}
        final_params["api_key"] = self._api_key
        try:
            async with self._session.get(self._url(endpoint), params=final_params, timeout=_PAID_TIMEOUT) as response:
                response.raise_for_status()
                json_data: dict[Any, Any] = await response.json()
                return json_data
        except aiohttp.ClientResponseError as exc:
            if exc.status not in (404, 429):
                logger.error(f"{type(exc).__name__}: {exc}")
            raise
        except (aiohttp.ClientConnectionError, aiohttp.ClientError, ValueError) as exc:
            logger.error(f"{type(exc).__name__}: {exc}")
            raise

    async def fetch_paid_uncached(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
        try:
            return await self.fetch_paid(endpoint, params)
        except aiohttp.ClientResponseError as exc:
            if exc.status == 404:
                logger.info(f"OpenDota 404 for '{endpoint}'; returning empty (will re-check next cycle).")
                return {}
            raise

    async def fetch_free_then_paid(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
        try:
            return await self.fetch_free(endpoint, params)
        except aiohttp.ClientResponseError as exc:
            if exc.status == 429:
                logger.warning(f"OpenDota free tier exhausted (429) for '{endpoint}'; retrying on the paid key.")
                return await self.fetch_paid(endpoint, params)
            raise


async def fetch_opendota(endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
    """Compatibility entry point for standalone callers; owns a short-lived session."""
    async with aiohttp_session_provider() as session:
        return await OpenDotaClient(session=session).fetch_free(endpoint, params)


@task(
    retries=3,
    retry_delay_seconds=5,
    retry_condition_fn=retry_if_not_404,
    cache_policy=TASK_SOURCE + INPUTS,
    cache_expiration=timedelta(days=1),
    persist_result=True,
)
async def fetch_opendota_api(endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
    """Cached paid API entry point for Prefect flows."""
    async with aiohttp_session_provider() as session:
        return await OpenDotaClient(session=session).fetch_paid(endpoint, params)


@task(retries=4, retry_delay_seconds=15, retry_condition_fn=retry_if_not_404)
async def fetch_opendota_api_uncached(endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
    """Uncached paid API entry point for Prefect flows."""
    async with aiohttp_session_provider() as session:
        return await OpenDotaClient(session=session).fetch_paid_uncached(endpoint, params)


async def fetch_opendota_free_then_paid(endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
    """Compatibility entry point for Prefect and standalone callers."""
    try:
        return await fetch_opendota(endpoint, params)
    except aiohttp.ClientResponseError as exc:
        if exc.status == 429:
            logger.warning(f"OpenDota free tier exhausted (429) for '{endpoint}'; retrying on the paid key.")
            return await fetch_opendota_api(endpoint, params)
        raise
