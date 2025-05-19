from .api_clients.opendota_api import fetch_opendota_api
from dota_oracle.pydantic_models.match import MatchesAPIResponse
from dota_oracle.config import ROOT_DIR
from dota_oracle.utils.set_logging import get_logger
from typing import Optional
from dota_oracle.utils.set_logging import get_logger
import logging
from pydantic import ValidationError

# Set up logger
logger = get_logger(__name__)
match_info_handler = logging.FileHandler(f'{ROOT_DIR}/logs/stored_pro_matchs.log')
handler_format = logging.Formatter('%(asctime)s - %(message)s')
match_info_handler.setFormatter(handler_format)
match_info_handler.addFilter(lambda record: record.levelno == logging.INFO)
logger.addHandler(match_info_handler)

async def fetch_match_details(match_id: str) -> Optional[MatchesAPIResponse]:
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

