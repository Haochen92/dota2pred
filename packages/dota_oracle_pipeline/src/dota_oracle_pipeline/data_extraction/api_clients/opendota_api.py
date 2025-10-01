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


async def fetch_opendota(endpoint: str, params: Optional[Dict[str, Any]] = None) -> dict[Any, Any]:
    # Free api calls
    # Normalize endpoint to avoid double slashes when callers pass leading '/'
    endpoint = endpoint.lstrip("/")
    url = f"{BASE_URL}{BASE_PATH}{endpoint}"
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, params=params) as res:
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
    """_summary_

    Fetch data from opendota API using paid API Key. Results with the same input and same function definition
    is cached, and set to expire in 1 day.
    Args:
        endpoint (str): the api endpoint
        params (Optional[Dict[str, Any]], optional): _description_. Defaults to None.

    Raises:
        ValueError: If API Key is missing

    Returns:
        dict[Any, Any]: Parsed JSON results from API
        
    """
    if not API_KEY:
        raise ValueError("Missing API KEY, unable to fetch data")
    # Paid api calls using API_KEY
    timeout = aiohttp.ClientTimeout(total=60)
    endpoint = endpoint.lstrip("/")
    url = f"{BASE_URL}{BASE_PATH}{endpoint}"

    final_params = params.copy() if params else {}
    final_params["api_key"] = API_KEY

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, params=final_params) as res:
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
    """
    Paid OpenDota API call without Prefect task caching.

    Raises ValueError if API key is missing.
    """
    if not API_KEY:
        raise ValueError("Missing API KEY, unable to fetch data")

    timeout = aiohttp.ClientTimeout(total=60)
    endpoint = endpoint.lstrip("/")
    url = f"{BASE_URL}{BASE_PATH}{endpoint}"

    final_params = params.copy() if params else {}
    final_params["api_key"] = API_KEY

    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            async with session.get(url, params=final_params) as res:
                res.raise_for_status()
                json_data: dict[Any, Any] = await res.json()
                return json_data
        except (aiohttp.ClientConnectionError, aiohttp.ClientError, aiohttp.http.HttpProcessingError, ValueError) as e:
            error_message = f"{type(e).__name__}: {str(e)}"
            logger.error(error_message)
            raise
