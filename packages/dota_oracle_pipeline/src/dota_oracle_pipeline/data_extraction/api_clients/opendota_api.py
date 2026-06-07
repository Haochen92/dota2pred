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


def retry_if_not_404(task, task_run, state) -> bool:
    """Prefect retry gate: retry transient errors but NOT a 404.

    A 404 ("not found") won't become found by retrying — e.g. a match OpenDota hasn't
    ingested yet — so retrying just burns retries x retry_delay for nothing (and risks the
    caller's time budget). It still *fails* (so it is not cached), and the caller decides
    what to do (return None / leave the item pending for a later cycle). Any other error is
    treated as transient and retried.
    """
    try:
        state.result(raise_on_failure=True)
    except aiohttp.ClientResponseError as exc:
        return exc.status != 404
    except Exception:
        return True
    return False


async def fetch_opendota(endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
    endpoint = endpoint.lstrip("/")
    url = f"{BASE_URL}{BASE_PATH}{endpoint}"
    session = _get_session()
    try:
        async with session.get(url, params=params, timeout=_FREE_TIMEOUT) as res:
            res.raise_for_status()
            json_data: dict[Any, Any] = await res.json()
            return json_data

    except aiohttp.ClientResponseError as cre:
        # A 429 on the free tier is expected once the daily/per-minute quota is spent, and
        # callers handle it (degrade to partial + paid per-match fallback). Logging it at ERROR
        # floods Grafana with non-actionable noise, so re-raise quietly and let the caller log.
        if cre.status != 429:
            logger.error(f"{type(cre).__name__}: {str(cre)}")
        raise
    except (aiohttp.ClientConnectionError, aiohttp.ClientError, aiohttp.http.HttpProcessingError, ValueError) as e:
        error_message = f"{type(e).__name__}: {str(e)}"
        logger.error(error_message)
        raise


@task(
    retries=3,
    retry_delay_seconds=5,
    retry_condition_fn=retry_if_not_404,
    cache_policy=TASK_SOURCE + INPUTS,
    cache_expiration=timedelta(days=1),
    # Explicit persist so the API-cost cache keeps working even with
    # PREFECT_RESULTS_PERSIST_BY_DEFAULT disabled globally.
    persist_result=True,
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

    except aiohttp.ClientResponseError as cre:
        # 429s are expected when a quota is spent and are retried/handled upstream; don't log
        # them at ERROR (non-actionable Grafana noise). Other HTTP errors are real.
        if cre.status != 429:
            logger.error(f"{type(cre).__name__}: {str(cre)}")
        raise
    except (aiohttp.ClientConnectionError, aiohttp.ClientError, aiohttp.http.HttpProcessingError, ValueError) as e:
        error_message = f"{type(e).__name__}: {str(e)}"
        logger.error(error_message)
        raise


@task(
    retries=4,
    retry_delay_seconds=15,
    retry_condition_fn=retry_if_not_404,
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
    except aiohttp.ClientResponseError as cre:
        if cre.status == 404:
            # Expected for not-yet-ingested / non-tracked matches. Return empty so the task
            # COMPLETES (no Failed-run pollution) and the caller treats it as "no data".
            # Uncached on purpose: the next stale cycle re-checks, which is what lets the
            # wait window catch slow/long matches when they finally appear on OpenDota.
            logger.info(f"OpenDota 404 for '{endpoint}'; returning empty (will re-check next cycle).")
            return {}
        # 429s are expected when a quota is spent and are retried by the task; don't log at
        # ERROR (non-actionable Grafana noise). Other HTTP errors are real.
        if cre.status != 429:
            logger.error(f"{type(cre).__name__}: {str(cre)}")
        raise
    except (aiohttp.ClientConnectionError, aiohttp.ClientError, aiohttp.http.HttpProcessingError, ValueError) as e:
        error_message = f"{type(e).__name__}: {str(e)}"
        logger.error(error_message)
        raise
