from .api_clients.opendota_api import fetch_opendota
from dota_oracle_common.models.leagues.schema import LeaguesAPIResponse, LeagueItem
import asyncio
from typing import List
from pydantic import ValidationError
from dota_oracle_common.utils.set_logging import get_logger

logger = get_logger(__name__)


async def fetch_league_data() -> List[LeagueItem]:

    try:
        res = await fetch_opendota(endpoint="leagues")
        if not res:
            return []
        validated_data = LeaguesAPIResponse.model_validate(res)
        list_league_items = validated_data.root
        return list_league_items
    except ValidationError as ve:
        logger.error(f"Validation Error: {ve}", exc_info=True)
        raise ve
    except Exception as e:
        logger.error("Error fetching leagues data:")
        raise e


if __name__ == "__main__":
    asyncio.run(fetch_league_data())
