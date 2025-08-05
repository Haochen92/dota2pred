from dota_oracle_common.utils.set_logging import get_logger
from typing import List
from ..services.redis_service import RedisService
from ..services.fetch_outcome_service import FetchOutcomeService
from dota_oracle_common.models.redis.schema import ConsumedEvent, CompletedMatchPayload
from dota_oracle_common.constants.redis_constants import STREAM_PENDING_COMPLETION

logger = get_logger(__name__)


class CompletionDataProvider:
    def __init__(
        self,
        redis_service: RedisService,
    ):
        self.redis = redis_service

    async def get_work_items(
        self, consumer_name: str = "default_consumer"
    ) -> List[ConsumedEvent[CompletedMatchPayload]]:

        # Fetch all pending events
        events = await self.redis.fetch_matches_for_completion(consumer_name)

        if not events:
            logger.info(f"No events in {STREAM_PENDING_COMPLETION}")
            return []

        # Extract list of match_ids from event list
        matches_pending_completion = [event.match_id for event in events]
        logger.info(f"Found {len(matches_pending_completion)} events pending completion")

        outcome_map = await FetchOutcomeService.fetch_outcomes_batch(matches_pending_completion)

        if not outcome_map:
            logger.info("None of the currently predicted live matches have completed")
            return []

        completed_match_list: List[ConsumedEvent[CompletedMatchPayload]] = []

        for event in events:
            match_id = event.match_id
            event_id = event.event_id
            if outcome_map.get(match_id):
                match_outcome = outcome_map[match_id]
                payload = CompletedMatchPayload(match_outcome=match_outcome)
                completed_match_list.append(
                    ConsumedEvent[CompletedMatchPayload](event_id=event_id, payload=payload, match_id=match_id)
                )

        return completed_match_list
