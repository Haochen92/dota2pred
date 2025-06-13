from .api_clients.opendota_api import fetch_opendota_api
from dota_oracle.models.match import MatchesAPIResponse
from dota_oracle.utils.set_logging import get_logger
from typing import Optional

from pydantic import ValidationError

# Set up logger
logger = get_logger(__name__)

async def fetch_match_details(match_id: int) -> Optional[MatchesAPIResponse]:
    endpoint = f'matches/{match_id}'
    try:
        res = await fetch_opendota_api(endpoint=endpoint)
        if not res:
            return None
        validated_input = MatchesAPIResponse(**res)
        return validated_input
        
    except ValidationError as ve:
        logger.error(f'Validation Error: {ve}', exc_info=True)
        raise ve
    except Exception as e:
        logger.error(f'Exception found: {e}', exc_info=True)
        raise e

