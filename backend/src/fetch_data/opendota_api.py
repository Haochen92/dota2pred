import aiohttp
from aiohttp import ClientSession
import pandas as pd
from tenacity import retry, stop_after_attempt, wait_fixed
from requests.exceptions import RequestException, Timeout, HTTPError
from middlewares.track_api import track_api_calls
from dotenv import load_dotenv
import os
from src.utils.set_logging import get_logger
from prefect.blocks.system import Secret

logger = get_logger(__name__)
load_dotenv()
API_KEY = Secret.load("opendota-api-key")


@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
async def fetch_opendota(query):
    # Free api calls
    url = f'http://api.opendota.com/api/{query}'
    timeout = aiohttp.ClientTimeout(total=120)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try: 
            async with session.get(url) as response:
                response.raise_for_status()
                json_data = await response.json()
                return response.status, json_data
                
        except (aiohttp.ClientConnectionError, aiohttp.ClientError, aiohttp.http.HttpProcessingError, ValueError) as e:
            error_message = f"{type(e).__name__}: {str(e)}"
            logger.error(error_message)
            raise
    
 
@track_api_calls
@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
async def fetch_opendota_api(url):
    # Paid api calls using API_KEY
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        params = {'api_key': API_KEY}
        try:
            async with session.get(url, params=params) as res:
                res.raise_for_status()
                json_data = await res.json()
                return res.status, json_data
                
        except (aiohttp.ClientConnectionError, aiohttp.ClientError, aiohttp.http.HttpProcessingError, ValueError) as e:
            error_message = f"{type(e).__name__}: {str(e)}"
            logger.error(error_message)
            raise


        

async def get_opendota_df(query):
    status, res = await fetch_opendota(query)
    
    if res and status == 200:
        try:
            # Attempt to convert the response to a DataFrame
            df = pd.DataFrame(res)
            return df
        except (ValueError, TypeError) as e:
            # Handle the case where the JSON data can't be converted into a DataFrame
            logger.error(f"Error converting response to DataFrame: {e}")
            return None
    else:
        logger.error(f"Failed with status code: {res.status_code if res else 'No response'}")
        return None


