from typing import List

from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.constants.redis_constants import STREAM_PENDING_ODDS
from dota_oracle_common.models.redis.schema import ConsumedEvent
from dota_oracle_common.models.odds import OddsResultPayload
from ..redis_services.redis_service import RedisService
from ..services.odds_market_service import OddsMarketService

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = "consumer_one"


class OddsDataProvider:
    """Data provider for the terminal odds-capture stage.

    Reads pending-odds events from Redis and resolves each into a storable snapshot (or a recorded
    no-market skip) via the OddsMarketService. Events left unresolved this cycle (transient errors
    within the snapshot window) are simply not returned, so they stay pending for a retry.
    """

    def __init__(self, redis_service: RedisService, odds_market_service: OddsMarketService):
        self.redis = redis_service
        self.odds_market_service = odds_market_service

    async def get_work_items(
        self, consumer_name: str = DEFAULT_CONSUMER_NAME
    ) -> List[ConsumedEvent[OddsResultPayload]]:
        pending_events = await self.redis.fetch_matches_for_odds(consumer_name)
        if not pending_events:
            logger.debug(f"No new events in {STREAM_PENDING_ODDS}")
            return []

        logger.info(f"Retrieved {len(pending_events)} events for odds capture")
        return await self.odds_market_service.resolve_snapshots(pending_events)
