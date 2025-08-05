from typing import List
from dota_oracle_common.utils.set_logging import get_logger
from live_orchestrator_app.services.redis_service import RedisService

from dota_oracle_common.models.redis.schema import (
    ConsumedEvent,
    FeatureEngineeringPayload,
)

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = "consumer_one"


class FeatureEngineeringDataProvider:
    """Data provider for feature engineering pipeline."""

    def __init__(self, redis_service: RedisService):
        self.redis = redis_service

    async def get_work_items(
        self, consumer_name: str = DEFAULT_CONSUMER_NAME
    ) -> List[ConsumedEvent[FeatureEngineeringPayload]]:
        """
        Fetches pending feature engineering events and corresponding match data.

        Args:
            consumer_name: Redis consumer name

        Returns:
            List of FeatureEngineeringWorkItem for processing
        """
        # Fetch pending events from Redis
        pending_events = await self.redis.fetch_new_matches_for_feature_eng(consumer_name)

        if not pending_events:
            logger.info("No events pending feature engineering")
            return []

        logger.info(f"Retrieved {len(pending_events)} pending events from Redis stream for feature engineering")

        return pending_events
