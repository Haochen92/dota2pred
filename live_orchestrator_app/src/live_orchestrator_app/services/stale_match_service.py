from datetime import timedelta

from ..redis_services.redis_service import RedisService
from ..constants.redis_constants import STREAM_PENDING_COMPLETION, COMPLETION_GROUP
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.async_utils import TaskRunner
from dota_oracle_common.utils.time_utils import get_current_utc_iso_timestamp, convert_redis_timestamp
from dota_oracle_common.models.redis.schema import CompletionPayload, ConsumedEvent, CompletedMatchPayload
from dota_oracle_common.models.utils.schema import AsyncTask
from dota_oracle_pipeline.data_extraction.fetch_match_details import fetch_match_details
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import List, Optional


logger = get_logger(__name__)


class StaleMatchService:
    def __init__(self, redis_service: RedisService):
        """_summary_
        Audit matches in pending_list of completion_stream.
        Any event which has not been processed within expiry_time
        will be claimed here and processed.

        args:
            redis_service (RedisService): RedisService Component
            expiry_time (float): duration to exceed to be eligible for claiming (in seconds)
        """
        self.redis = redis_service
        self.stream = STREAM_PENDING_COMPLETION
        self.group = COMPLETION_GROUP
        self.expiry_duration = 5400
        self.batch_size = 50
        # A match still unavailable on OpenDota after this long is treated as never coming
        # (abandoned/private/not a tracked pro match) and terminally discarded. Pro matches are
        # parsed by OpenDota within minutes-to-an-hour, so a 404 past this window is almost
        # certainly never resolving; if it ever is real, the proMatches -> DB batch backfill
        # still captures it independently of this live stream.
        self.max_pending_age = timedelta(hours=2)

    async def run_stream_cleaning_cycle(
        self, consumer_name: str = "stale_match_consumer"
    ) -> List[ConsumedEvent[CompletedMatchPayload]]:
        """
        Scan through the pending list to check for poisoned events and process them
        """
        try:
            # Fetch expired messages longer than expiry duration
            expired_pending_messages = await self.redis.fetch_expired_events(
                stream_name=self.stream, consumer_group=self.group, duration=self.expiry_duration
            )
        except Exception as e:
            logger.error(
                f"Error encountered while fetching expired_pending_messesages from redis_service, {e}", exc_info=True
            )
            raise

        if not expired_pending_messages:
            return []

        # Bound per-cycle work. StaleMatchService is the small real-time tail handler, not a
        # bulk backfiller (that is sync_pro_matches / scheduled_backfill). Capping keeps a
        # large backlog draining as a trickle so it can't dominate the live cycle's timeout.
        if len(expired_pending_messages) > self.batch_size:
            logger.info(
                f"Capping stale sweep from {len(expired_pending_messages)} to {self.batch_size} this cycle; "
                "remainder drains over subsequent cycles (bulk recovery is the scheduled backfill's job)."
            )
            expired_pending_messages = expired_pending_messages[: self.batch_size]

        try:
            claimed_expired_events = await self.redis.claim_expired_events(
                stream_name=self.stream,
                consumer_group=self.group,
                payload_model=CompletionPayload,
                consumer_name=consumer_name,
                events_id_list=expired_pending_messages,
            )
        except Exception as e:
            logger.error(f"Error encountered while claiming expired events from redis_service, {e}", exc_info=True)
            raise

        completed_matches = await self._fetch_completed_work_items(claimed_expired_events)

        info_msg = f"""
            Found {len(expired_pending_messages)} expired_messages
            Successfully claimed {len(claimed_expired_events)}
            with {len(completed_matches)} / {len(claimed_expired_events)} completed without errors
            and {len(claimed_expired_events) - len(completed_matches)} moved to DLQ
        """
        logger.info(info_msg)

        return completed_matches

    async def _fetch_completed_work_items(
        self, claimed_expired_events: List[ConsumedEvent[CompletionPayload]]
    ) -> List[ConsumedEvent[CompletedMatchPayload]]:
        completed_matches_events: List[ConsumedEvent[CompletedMatchPayload]] = []

        concurrent_tasks = [
            AsyncTask(key=event.event_id, inputs=event, coro=self._fetch_single_completed_match(event))
            for event in claimed_expired_events
        ]

        results = await TaskRunner.run_concurrently(concurrent_tasks, concurrency_limit=20)

        for res in results:
            event_id = res.key
            original_event = res.inputs
            match_id = original_event.match_id
            try:
                match_outcome = res.outcome

                if isinstance(match_outcome, BaseException):
                    raise match_outcome

                if match_outcome is None:
                    # Not available on OpenDota yet (404). Normally leave it pending to retry on
                    # a later cycle, but if it has been pending longer than max_pending_age it is
                    # almost certainly never coming (abandoned/private) -> dead-letter it.
                    pending_age = get_current_utc_iso_timestamp() - convert_redis_timestamp(event_id)
                    if pending_age > self.max_pending_age:
                        logger.warning(f"Match {match_id} still unavailable after {pending_age}; discarding.")
                        # Terminal discard (XACK + XDEL), NOT the retryable DLQ -- otherwise the
                        # DLQ sweep re-injects it and the same unresolvable match churns forever.
                        await self.redis.discard_unresolvable_event(
                            match_id=match_id,
                            event_id=event_id,
                            consumer_group=self.group,
                            event_stream=self.stream,
                            reason=f"not on OpenDota after {pending_age}",
                        )
                    continue

                completed_match_msg = ConsumedEvent(
                    match_id=match_id, event_id=event_id, payload=CompletedMatchPayload(match_outcome=match_outcome)
                )

                completed_matches_events.append(completed_match_msg)
            except Exception as e:
                await self.redis.handle_processing_failure(
                    event_data=original_event,
                    event_id=event_id,
                    error=e,
                    consumer_group=self.group,
                    event_stream=self.stream,
                )
                continue

        return completed_matches_events

    # Retry only genuinely transient errors (fetch_match_details raises on those). A 404
    # returns None and must NOT be retried -- it just means "not ingested yet", which would
    # otherwise block for ~30s/match and risk the live cycle timeout. Kept short and bounded.
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
    async def _fetch_single_completed_match(self, event: ConsumedEvent[CompletionPayload]) -> Optional[bool]:
        match_id = event.payload.match_id
        match_details = await fetch_match_details(match_id)
        if match_details is None:
            # Not available on OpenDota yet (404): leave pending, no retry, no DLQ.
            logger.info(f"Match {match_id} not available on OpenDota yet; leaving pending for a later cycle.")
            return None
        return bool(match_details.radiant_win)
