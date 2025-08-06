from dota_oracle_common.utils.set_logging import get_logger
from ..services.feature_engineering_service import FeatureEngineeringService
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from dota_oracle_common.models.redis.schema import ConsumedEvent, FeatureEngineeringPayload, PredictionPayload
from dota_oracle_common.models.match import MatchTable


logger = get_logger(__name__)


class FeatureEngineeringEventProcessor:
    """Event processor for handling single feature engineering work items."""

    def __init__(
        self,
        feature_engineering_service: FeatureEngineeringService,
        db_session_factory: async_sessionmaker[AsyncSession],
    ):
        self.feature_engineering_service = feature_engineering_service
        self.db_session_factory = db_session_factory

    async def process_event(self, event: ConsumedEvent[FeatureEngineeringPayload]) -> PredictionPayload:
        """
        Processes a single feature engineering work item.
        Creates its own transaction for this unit of work.

        Args:
            work_item: FeatureEngineeringWorkItem containing event and match data
        """
        match_id = event.match_id
        match_details = event.payload.match_details

        async with self.db_session_factory() as session:
            async with session.begin():
                try:
                    logger.debug(f"Processing feature engineering for match_id={match_id}")

                    match_table_data = MatchTable.model_validate(match_details)
                    # Create and store features with session
                    hero_features, team_features, player_hero_features = (
                        await self.feature_engineering_service.create_and_store_features(match_table_data, session)
                    )

                    logger.debug(f"Successfully processed feature engineering for match_id={match_id}")
                    return PredictionPayload(
                        hero_features=hero_features,
                        team_features=team_features,
                        player_hero_features=player_hero_features,
                    )

                except Exception as e:
                    logger.error(
                        f"Failed to process feature engineering for match_id={match_id}: {e}",
                        exc_info=True,
                    )
                    raise e
