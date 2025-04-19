import aiohttp
from datetime import timedelta
from prefect import task
from prefect.cache_policies import INPUTS, TASK_SOURCE
from middlewares.track_api import track_api_calls
from dotenv import load_dotenv
import os
from src.utils.set_logging import get_logger
from typing import Optional

logger = get_logger(__name__)
load_dotenv()
API_KEY = os.getenv('OPEN_DOTA_API')
BASE_URL = 'https://api.opendota.com'
BASE_PATH = '/api/'

@task(retries=3, retry_delay_seconds=2, cache_policy=INPUTS + TASK_SOURCE, cache_expiration=timedelta(days=1))
async def fetch_opendota(endpoint: str, params: Optional[dict] = None ):
    # Free api calls
    url = f'{BASE_URL}{BASE_PATH}{endpoint}'
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try: 
            async with session.get(url, params=params) as res:
                res.raise_for_status()
                json_data = await res.json()
                return json_data
                
        except (aiohttp.ClientConnectionError, aiohttp.ClientError, aiohttp.http.HttpProcessingError, ValueError) as e:
            error_message = f"{type(e).__name__}: {str(e)}"
            logger.error(error_message)
            raise
    
 
@track_api_calls
@task(retries=3, retry_delay_seconds=2)
async def fetch_opendota_api(url):
    # Paid api calls using API_KEY
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        params = {'api_key': API_KEY}
        try:
            async with session.get(url, params=params) as res:
                res.raise_for_status()
                json_data = await res.json()
                return json_data
                
        except (aiohttp.ClientConnectionError, aiohttp.ClientError, aiohttp.http.HttpProcessingError, ValueError) as e:
            error_message = f"{type(e).__name__}: {str(e)}"
            logger.error(error_message)
            raise




