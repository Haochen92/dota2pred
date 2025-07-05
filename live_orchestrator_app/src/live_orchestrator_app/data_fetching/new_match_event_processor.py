from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_pipeline.data_transformation.live_match_parser import parse_live_league_games
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.models.match import MatchTable
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from dota_oracle_common.models.pipeline import NewMatchWorkItem

logger = get_logger(__name__)


class NewMatchEventProcessor:
    """Event processor for handling single new match work items."""

    def __init__(self, db_engine: AsyncEngine):
        self.engine = db_engine

    async def process_event(self, work_item: NewMatchWorkItem) -> None:
        """
        Processes a single new match work item.
        Creates its own transaction for this unit of work.

        Args:
            work_item: NewMatchWorkItem containing match data to process
        """
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                try:
                    # Transform match data
                    transformed_match = await self._transform_match_data(work_item, session)

                    # Store match details
                    await self._store_match_details(transformed_match, session)

                    logger.debug(f"Successfully processed new match {work_item.match_id}")

                except Exception as e:
                    logger.error(f"Failed to process new match {work_item.match_id}: {e}", exc_info=True)
                    raise e

    async def _transform_match_data(self, work_item: NewMatchWorkItem, session: AsyncSession) -> MatchTable:
        """Transforms live match data to MatchTable."""
        try:
            transformed_data = await parse_live_league_games([work_item.live_match_data])

            if not transformed_data:
                raise ValueError(f"Failed to transform match data for match {work_item.match_id}")

            return transformed_data[0]

        except Exception as e:
            logger.error(f"Unable to transform live match data for match {work_item.match_id}: {e}", exc_info=True)
            raise

    async def _store_match_details(self, match_data: MatchTable, session: AsyncSession) -> None:
        """Stores match details in database."""
        try:
            match_repository = MatchRepository(session=session)
            await match_repository.insert_match_details([match_data])

        except Exception as e:
            logger.error(f"Failed to store match details for match {match_data.match_id}: {e}", exc_info=True)
            raise
