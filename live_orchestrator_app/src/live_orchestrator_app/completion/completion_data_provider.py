from datetime import timedelta
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.time_utils import get_current_utc_iso_timestamp, convert_redis_timestamp
from typing import List
from ..redis_services.redis_service import RedisService
from ..services.fetch_outcome_service import FetchOutcomeService
from ..services.stale_match_service import StaleMatchService
from ..constants.match_constants import COMPLETION_FREE_FEED_WINDOW_SECONDS
from dota_oracle_common.models.redis.schema import ConsumedEvent, CompletedMatchPayload
from dota_oracle_common.constants.redis_constants import STREAM_PENDING_COMPLETION

logger = get_logger(__name__)


class CompletionDataProvider:
    def __init__(self, redis_service: RedisService, stale_match_service: StaleMatchService):
        self.redis = redis_service
        self.stale_match_service = stale_match_service

    async def get_work_items(
        self, consumer_name: str = "default_consumer"
    ) -> List[ConsumedEvent[CompletedMatchPayload]]:
        """Resolve completed matches via two independent paths.

        The fresh path (free /proMatches) and the stale recovery path (paid per-match
        StaleMatchService) are isolated: a failure or empty result in one must not stop
        the other. The stale sweep therefore runs every cycle, regardless of the fresh
        fetch — otherwise a quiet period (no fresh completions) or a fresh-fetch error
        would permanently starve recovery of aged/poison pending messages.
        """
        completed_match_list: List[ConsumedEvent[CompletedMatchPayload]] = []

        # --- Fresh path: best-effort resolution of newly-pending matches via the free feed ---
        try:
            events = await self.redis.fetch_matches_for_completion(consumer_name)
            # Only hit the free /proMatches feed for matches young enough to still be near its
            # top. Aged matches can't be found within the small page budget and would only drag
            # the id-range back through history (burning the free quota for nothing) -- they
            # belong to the paid per-match stale path, which claims them once they cross this same
            # window. So skip them here and let the stale sweep handle them.
            cutoff = get_current_utc_iso_timestamp() - timedelta(seconds=COMPLETION_FREE_FEED_WINDOW_SECONDS)
            fresh_events = [event for event in events if convert_redis_timestamp(event.event_id) >= cutoff]
            if fresh_events:
                matches_pending_completion = [event.match_id for event in fresh_events]
                logger.info(f"Found {len(matches_pending_completion)} fresh events pending completion")

                outcome_map = await FetchOutcomeService.fetch_outcomes_batch(matches_pending_completion)
                for event in fresh_events:
                    match_outcome = outcome_map.get(event.match_id)
                    if match_outcome is not None:
                        completed_match_list.append(
                            ConsumedEvent[CompletedMatchPayload](
                                event_id=event.event_id,
                                payload=CompletedMatchPayload(match_outcome=match_outcome),
                                match_id=event.match_id,
                            )
                        )
            else:
                logger.info(f"No fresh events in {STREAM_PENDING_COMPLETION}")
        except Exception as e:
            logger.error(f"Fresh completion fetch failed; continuing to stale sweep. {e}", exc_info=True)

        # --- Stale recovery path: independent, runs every cycle ---
        try:
            completed_stale_matches = await self.stale_match_service.run_stream_cleaning_cycle("stale_match_consumer")
            completed_match_list.extend(completed_stale_matches)
        except Exception as e:
            logger.error(f"Stale match sweep failed this cycle. {e}", exc_info=True)

        return completed_match_list
