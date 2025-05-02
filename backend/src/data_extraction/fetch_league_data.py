from .api_clients.opendota_api import fetch_opendota
from pydantic_models.leagues import LeaguesAPIResponse, LeagueItem
from src.config import ROOT_DIR
import asyncio
from typing import List
from pydantic import ValidationError
from utils.set_logging import get_logger

logger = get_logger(__name__)

league_constants_fpth = ROOT_DIR / "constants"/ "league_ids.yml"

async def fetch_league_data() -> List[LeagueItem]:
    
    try:
        res = await fetch_opendota(endpoint='leagues')
        if not res:
            return []
        validated_data = LeaguesAPIResponse(res)
        list_league_items = validated_data.root
        return list_league_items
    except ValidationError as ve:
        logger.error(f'Validation Error: {ve}', exe_info=True)
        raise ve
    except Exception as e:
        logger.error(f'Error fetching leagues data:')
        raise e
    
    
        
        
if __name__ == "__main__":
    asyncio.run(fetch_league_data())