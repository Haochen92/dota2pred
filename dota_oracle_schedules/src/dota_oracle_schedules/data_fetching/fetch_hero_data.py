from prefect import flow
from dota_oracle_common.postgresql import DatabaseManager
from dota_oracle_common.utils import get_logger
from dota_oracle_common.repositories.heroes_repository import HeroesRepository
from dota_oracle_common.models.heroes import HeroDataTable, HeroData
from dota_oracle_pipeline.data_extraction.fetch_hero_data import fetch_hero_data
from pydantic import ValidationError
from typing import Dict
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


@flow
async def hero_data_orchestrator():
    # fetch hero data from api endpoint
    hero_data = await fetch_hero_data()

    local_session = DatabaseManager.get_session_factory()

    # Store data
    async with local_session() as session:
        async with session.begin():
            try:
                await store_hero_data(session, hero_data)
            except Exception as e:
                raise e

    logger.info("Successfully updated hero data")


async def store_hero_data(session: AsyncSession, hero_data_dict: Dict[str, HeroData]) -> None:
    hero_data_table: Dict[str, HeroDataTable] = {}
    for key, hero_data in hero_data_dict.items():
        try:
            hero_data_table[key] = HeroDataTable.model_validate(hero_data)
        except ValidationError as e:
            logger.error(f"Validation error for hero data dict, {e}", exc_info=True)
            raise

    hero_repo = HeroesRepository(session)
    try:
        await hero_repo.upsert_hero_data(hero_data_table)
    except Exception as e:
        logger.error(f"Error encountered while storing hero table data, {e}", exc_info=True)
        raise
