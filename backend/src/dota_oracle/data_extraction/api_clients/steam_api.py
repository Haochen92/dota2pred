import os
import aiohttp
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

STEAM_URL = 'http://api.steampowered.com/'
API_KEY = os.getenv('STEAM_API')


async def fetch_steam_data(endpoint: str) -> Optional[dict]:
    url = f'{STEAM_URL}{endpoint}'
    async with aiohttp.ClientSession() as session:
        params = {'key':API_KEY}
        async with session.get(url, params=params) as response:
            if response.status != 200:
                raise ValueError(f"Request failed with status {response.status}, retrying...")
            
            response_json = await response.json()
            
            if not response_json:
                raise ValueError("Empty dictionary, retrying...")
            
            return response_json