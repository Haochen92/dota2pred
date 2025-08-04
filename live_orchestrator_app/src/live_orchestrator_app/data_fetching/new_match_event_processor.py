from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_pipeline.data_transformation.live_match_parser import parse_live_league_games
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.models.match import MatchTable
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from live_orchestrator_app.services.redis_service import RedisService
from dota_oracle_common.models.live_games.schema import OngoingLeagueGame

logger = get_logger(__name__)


class NewMatchEventProcessor:
    """Event processor for handling single new match work items."""

    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession], redis_service: RedisService):
        self.db_session_factory = db_session_factory
        self.redis = redis_service

    async def process_event(self, ongoing_match: OngoingLeagueGame) -> None:
        """
        Processes a new match: transforms, stores in DB, and publishes to Redis.
        Returns the transformed MatchTable upon success.

        Args:
            work_item: NewMatchWorkItem containing match data to process
        """
        try:
            # Transform data
            transformed_match = await self._transform_match_data(ongoing_match)

            # Store in database
            await self._store_match_details(transformed_match)

            # Publish payload to redis
            await self.redis.publish_new_match_to_feature_eng(transformed_match)

            logger.info(f"Successfully processed and published new match {transformed_match.match_id}")

        except Exception as e:
            logger.error(f"Failed to process new match {ongoing_match.match_id}: {e}", exc_info=True)
            raise e

    async def _transform_match_data(self, ongoing_match: OngoingLeagueGame) -> MatchTable:
        """Transforms live match data to MatchTable."""
        try:
            transformed_data = await parse_live_league_games([ongoing_match])  # expects a list

            if not transformed_data:
                raise ValueError(f"Failed to transform match data for match {ongoing_match.match_id}")

            return transformed_data[0]

        except Exception as e:
            logger.error(f"Unable to transform live match data for match {ongoing_match.match_id}: {e}", exc_info=True)
            raise

    async def _store_match_details(self, match_data: MatchTable) -> None:
        """Stores match details in database."""
        async with self.db_session_factory() as session:
            async with session.begin():
                try:
                    match_repository = MatchRepository(session=session)
                    await match_repository.insert_match_details([match_data])

                except Exception as e:
                    logger.error(f"Failed to store match details for match {match_data.match_id}: {e}", exc_info=True)
                    raise
