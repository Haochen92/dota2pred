from .api_clients.steam_api import fetch_steam_data
from typing import List
import asyncio
from dota_oracle.utils.set_logging import get_logger
from dota_oracle.pydantic_models.live_league_games import LiveLeagueAPIResponse, LiveLeagueGame
from pydantic import ValidationError

logger = get_logger(__name__)

# Constants
LIVE_LEAGUE_GAMES = 'IDOTA2Match_570/GetLiveLeagueGames/v1'

async def fetch_live_league_games() -> List[LiveLeagueGame]:
    try:
        res = await fetch_steam_data(endpoint=LIVE_LEAGUE_GAMES)
        validated_res = LiveLeagueAPIResponse(**res)
        games_list = validated_res.result.games
        return games_list
    except ValidationError as ve:
        logger.error(f"API response validation failed: {ve}", exc_info=True)
        raise ve # 
    except Exception as e:
        logger.error(f"Error fetching live_league_games: {e}", exc_info=True)
        raise e
         



if __name__ == '__main__':
    asyncio.run(fetch_live_league_games())