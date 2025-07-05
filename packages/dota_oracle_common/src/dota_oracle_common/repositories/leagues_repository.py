from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from ..utils.set_logging import get_logger
from ..models.leagues import LeagueTable
from .base_repository import BaseRepository

logger = get_logger(__name__)


class LeaguesRepository(BaseRepository):
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def store_league_data(self, league_inputs: List[LeagueTable]) -> None:

        try:
            await self._insert_data(model_class=LeagueTable, instances=league_inputs)
        except Exception as e:
            logger.error(f"Error encountered when storing league data: Error {e}", exc_info=True)
            raise e

    async def get_league_data_by_ids(self, league_id_inputs: List[int]) -> List[LeagueTable]:
        try:
            league_data_instances = await self._get_data(model_class=LeagueTable, id_filters=league_id_inputs)
            if not league_data_instances:
                logger.debug(f"No data found for league_ids, {league_id_inputs}")
                return []
            return league_data_instances
        except Exception as e:
            logger.error(f"Error fetching league_data for league_ids: {league_id_inputs},{e}", exc_info=True)

    async def get_all_league_data(self) -> List[LeagueTable]:
        try:
            all_league_data = await self._get_data(model_class=LeagueTable)
            if not all_league_data:
                logger.warning(f"Table {LeagueTable.__tablename__} is empty")
                return []

            logger.info(f"Found {len(all_league_data)} league data entries")
            return all_league_data
        except Exception as e:
            logger.error(f"Error encountered while fetching all league data, error: {e}", exc_info=True)
            raise
