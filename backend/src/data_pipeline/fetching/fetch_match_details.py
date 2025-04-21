from prefect import task 
import logging
from data_pipeline.fetching.api.opendota_api import fetch_opendota_api
from pydantic_models import Match
from datetime import timedelta 
from src.config import ROOT_DIR
from src.utils.set_logging import get_logger
from prefect.cache_policies import INPUTS, TASK_SOURCE
from typing import Optional

# Set up logger
logger = get_logger(__name__)
match_info_handler = logging.FileHandler(f'{ROOT_DIR}/logs/stored_pro_matchs.log')
handler_format = logging.Formatter('%(asctime)s - %(message)s')
match_info_handler.setFormatter(handler_format)
match_info_handler.addFilter(lambda record: record.levelno == logging.INFO)
logger.addHandler(match_info_handler)

@task(retries=3, retry_delay_seconds=2, cache_policy=INPUTS + TASK_SOURCE, cache_expiration=timedelta(days=10))
async def get_match_details(match_id: str) -> Optional[Match]:
    url = f'http://api.opendota.com/api/matches/{match_id}'
    status, res = await fetch_opendota_api(url)
    
    if res and status == 200:
        return Match(**res)
    else:
        logger.error(f"Failed with status code: {res.status_code if res else 'No response'}")

        return None    


