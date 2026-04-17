from typing import List
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.constants.redis_constants import STREAM_PENDING_PREDICTION
from live_orchestrator_app.redis_services.redis_service import RedisService
from dota_oracle_common.models.redis.schema import (
    ConsumedEvent,
    PredictionPayload,
)

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = "consumer_one"


class PredictionDataProvider:
    """Data provider for prediction pipeline."""

    def __init__(self, redis_service: RedisService):
        self.redis = redis_service

    async def get_work_items(
        self, consumer_name: str = DEFAULT_CONSUMER_NAME
    ) -> List[ConsumedEvent[PredictionPayload]]:
        """
        Fetches pending prediction events from Redis.

        Args:
            consumer_name: Redis consumer name

        Returns:
            List of ConsumedEvents with prediction payload
        """
        logger.debug(f"Fetching events from stream '{STREAM_PENDING_PREDICTION}'")

        # Fetch pending events from Redis
        pending_events = await self.redis.fetch_matches_for_prediction(consumer_name)

        if not pending_events:
            logger.debug(f"No new events in {STREAM_PENDING_PREDICTION}")
            return []

        logger.info(f"Retrieved {len(pending_events)} events for prediction")

        return pending_events
