from .api_clients.opendota_api import fetch_opendota_api
from pydantic_models import Match
from src.config import ROOT_DIR
from src.utils.set_logging import get_logger
from typing import Optional
from utils.set_logging import get_logger
import logging

# Set up logger
logger = get_logger(__name__)
match_info_handler = logging.FileHandler(f'{ROOT_DIR}/logs/stored_pro_matchs.log')
handler_format = logging.Formatter('%(asctime)s - %(message)s')
match_info_handler.setFormatter(handler_format)
match_info_handler.addFilter(lambda record: record.levelno == logging.INFO)
logger.addHandler(match_info_handler)

async def fetch_match_details(match_id: str) -> Optional[Match]:
    url = f'http://api.opendota.com/api/matches/{match_id}'
    status, res = await fetch_opendota_api(url)
    
    if res and status == 200:
        return Match(**res)
    else:
        logger.error(f"Failed with status code: {res.status_code if res else 'No response'}")
        return None    


