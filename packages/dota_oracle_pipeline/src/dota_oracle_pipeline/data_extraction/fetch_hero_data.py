from .api_clients.opendota_api import fetch_opendota_free_then_paid
from dota_oracle_common.models.heroes import HeroesAPIResponse, HeroData
import asyncio
from dota_oracle_common.utils.set_logging import get_logger
from pydantic import ValidationError
from typing import Dict

logger = get_logger(__name__)


async def fetch_hero_data() -> Dict[str, HeroData]:
    try:
        # fetch hero constants from OpenDota's API
        res = await fetch_opendota_free_then_paid(endpoint="constants/heroes")
        if not res:
            logger.info("No data found")
            return {}
        validated_data = HeroesAPIResponse(res)
        hero_data_dict = validated_data.root
        return hero_data_dict
    except ValidationError as ve:
        logger.error(f"Data Validation error {ve}")
        raise ve
    except Exception as e:
        logger.error(f"Error at fetching heroes_data: {e}")
        raise e


if __name__ == "__main__":
    asyncio.run(fetch_hero_data())
