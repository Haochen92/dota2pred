from .api_clients.opendota_api import fetch_opendota_api
from dota_oracle_common.models.match import MatchesAPIResponse
from dota_oracle_common.utils import get_logger
from typing import Optional
from pydantic import ValidationError
import aiohttp

# Set up logger
logger = get_logger(__name__)


async def fetch_match_details(match_id: int) -> Optional[MatchesAPIResponse]:
    endpoint = f"matches/{match_id}"
    try:
        res = await fetch_opendota_api(endpoint=endpoint)
        if not res:
            return None
        validated_input = MatchesAPIResponse(**res)
        return validated_input
    except aiohttp.ClientResponseError as cre:
        # OpenDota can return 404 for matches that are not yet ingested or unavailable
        if cre.status == 404:
            logger.info(f"Match {match_id} not available yet on OpenDota (404). Will retry later.")
            return None
        logger.error(f"HTTP error for match {match_id}: {cre}", exc_info=True)
        raise
    except ValidationError as ve:
        logger.error(f"Validation Error: {ve}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Exception found: {e}", exc_info=True)
        raise
