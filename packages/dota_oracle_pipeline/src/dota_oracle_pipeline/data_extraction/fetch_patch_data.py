from .api_clients.opendota_api import fetch_opendota_free_then_paid
from dota_oracle_common.models.patches import DotaPatchAPIResponse, DotaPatch
from dota_oracle_common.utils.set_logging import get_logger
from typing import List
from pydantic import ValidationError
import aiohttp

logger = get_logger(__name__)


async def fetch_patch_data() -> List[DotaPatch]:
    """
    Fetch Dota patch data from OpenDota API.

    Returns:
        List[DotaPatch]: List of patch data with parsed datetime

    Raises:
        aiohttp.ClientError: For API connection issues
        ValidationError: For data validation failures
        Exception: For unexpected errors
    """
    try:
        logger.info("Fetching patch data from OpenDota API")
        res = await fetch_opendota_free_then_paid(endpoint="constants/patch")

        api_response = DotaPatchAPIResponse.model_validate(res)
        patch_list = api_response.root

        logger.info(f"Successfully fetched {len(patch_list)} patches")
        return patch_list

    except (
        aiohttp.ClientConnectionError,
        aiohttp.ClientError,
        aiohttp.http.HttpProcessingError,
        ValueError,
        ValidationError,
    ) as e:
        error_message = f"{type(e).__name__}: {str(e)}"
        logger.error(error_message, exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Exception while fetching patch data: {e}", exc_info=True)
        raise
