from prefect import flow
from dota_oracle_common.postgresql import database_session_factory_resource
from dota_oracle_common.utils import get_logger
from dota_oracle_common.repositories.leagues_repository import LeaguesRepository
from dota_oracle_common.models.leagues import LeagueTable, LeagueItem
from dota_oracle_pipeline.data_extraction.fetch_league_data import fetch_league_data
from pydantic import ValidationError
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


@flow
async def league_data_orchestrator():
    async with database_session_factory_resource() as session_factory:
        # fetch league data from api endpoint
        league_data = await fetch_league_data()

        # Store data
        async with session_factory() as session:
            async with session.begin():
                try:
                    await store_league_data(session, league_data)
                except Exception as e:
                    raise e

    logger.info("Successfully updated league data")


async def store_league_data(session: AsyncSession, league_data_items: List[LeagueItem]) -> None:
    league_data_table: List[LeagueTable] = []
    for league_item in league_data_items:
        try:
            league_data_table.append(LeagueTable.model_validate(league_item))
        except ValidationError as e:
            logger.error(f"Validation error for league data item, {e}", exc_info=True)
            raise

    league_repo = LeaguesRepository(session)
    try:
        await league_repo.store_league_data(league_data_table)
    except Exception as e:
        logger.error(f"Error encountered while storing league table data, {e}", exc_info=True)
        raise
