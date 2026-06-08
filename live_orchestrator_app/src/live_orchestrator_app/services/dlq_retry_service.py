import json
import os
from typing import Optional

from dota_oracle_common.constants.redis_constants import FAILED_EVENTS_MAPPING, DLQ_RETRY_COUNT_PREFIX
from dota_oracle_common.models.redis.schema import FailureRecord
from dota_oracle_common.utils.set_logging import get_logger
from ..constants.payload_mappings import PAYLOAD_MODEL_MAPPING
from ..redis_services.redis_service import RedisService

logger = get_logger(__name__)

# A retry count must outlive the individual DLQ entries it tracks: a DLQ entry is deleted on
# reinject and a fresh one (new event id) is created if the match fails again, so the count is
# keyed by the stable match id, not the event id. A TTL makes it self-cleaning -- a count whose
# match eventually *succeeds* is never explicitly deleted, so without a TTL it would leak (the
# original design swept a separate hash to GC these, which was both extra machinery and the source
# of a churn bug). The TTL is refreshed on every increment and is comfortably longer than any retry
# sequence, so it only fires once a match has genuinely left the pipeline. Mirrors the match_status
# hash's self-cleaning TTL.
DLQ_RETRY_COUNT_TTL_SECONDS = int(os.getenv("DLQ_RETRY_COUNT_TTL_SECONDS", str(6 * 3600)))


class DlqRetryService:
    def __init__(self, redis_service: RedisService, max_retries: int = 3):
        self.redis_service = redis_service
        self.redis = redis_service.redis
        self.max_retries = max_retries

    async def run_retry_sweep(self) -> int:
        """Sweep all DLQ hashes and reinject eligible events. Returns total reinjected count."""
        total_reinjected = 0

        for stream_name, dlq_hash_name in FAILED_EVENTS_MAPPING.items():
            try:
                reinjected = await self._process_dlq_hash(stream_name, dlq_hash_name)
                total_reinjected += reinjected
            except Exception as e:
                logger.error(f"Error processing DLQ hash '{dlq_hash_name}': {e}", exc_info=True)

        if total_reinjected:
            logger.info(f"DLQ sweep: reinjected {total_reinjected} events")

        return total_reinjected

    async def _process_dlq_hash(self, stream_name: str, dlq_hash_name: str) -> int:
        """Process a single DLQ hash. Returns number of events reinjected."""
        raw_events = await self.redis.hgetall(dlq_hash_name)  # type: ignore[misc]  # redis-py async union-return
        if not raw_events:
            return 0

        reinjected = 0
        for event_id, event_json in raw_events.items():
            record = self._parse_failure_record(event_id, event_json, stream_name)
            if record is None:
                continue

            match_id = record.original_data.match_id
            retry_key = f"{stream_name}:{match_id}"
            retry_count = await self._get_retry_count(retry_key)

            if retry_count >= self.max_retries:
                # Retries exhausted: this failure won't be fixed by retrying, so drop it for
                # good (remove from the DLQ and forget its count) instead of leaving it to be
                # re-evaluated -- and logged -- on every future sweep. If the match's data ever
                # becomes valid, the batch backfill still captures it independently.
                logger.warning(
                    f"DLQ: match {match_id} in '{stream_name}' exhausted {self.max_retries} retries; "
                    "dropping permanently"
                )
                await self._drop_exhausted_event(record, dlq_hash_name, retry_key)
                continue

            success = await self._reinject_event(record, dlq_hash_name, retry_key)
            if success:
                reinjected += 1

        return reinjected

    @staticmethod
    def _count_key(retry_key: str) -> str:
        """Redis key holding the retry count for a (stream, match_id) pair."""
        return f"{DLQ_RETRY_COUNT_PREFIX}:{retry_key}"

    async def _drop_exhausted_event(self, record: FailureRecord, dlq_hash_name: str, retry_key: str) -> None:
        """Permanently remove a retry-exhausted event from the DLQ and forget its retry count."""
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.hdel(dlq_hash_name, record.original_event_id)
                pipe.delete(self._count_key(retry_key))
                await pipe.execute()
        except Exception as e:
            logger.error(f"DLQ: failed to drop exhausted event {record.original_event_id}: {e}", exc_info=True)

    def _parse_failure_record(self, event_id: str, event_json: str, stream_name: str) -> Optional[FailureRecord]:
        """Parse a raw DLQ entry into a typed FailureRecord."""
        try:
            raw_dict = json.loads(event_json)
            PayloadType = PAYLOAD_MODEL_MAPPING.get(stream_name)
            if not PayloadType:
                logger.warning(f"DLQ: unknown stream '{stream_name}' for event {event_id}")
                return None

            FailureModel = FailureRecord[PayloadType]
            return FailureModel.model_validate(raw_dict)
        except Exception as e:
            logger.error(f"DLQ: failed to parse event {event_id}: {e}")
            return None

    async def _get_retry_count(self, retry_key: str) -> int:
        """Get the current retry count for a match from its TTL'd count key."""
        count = await self.redis.get(self._count_key(retry_key))
        return int(count) if count else 0

    async def _reinject_event(self, record: FailureRecord, dlq_hash_name: str, retry_key: str) -> bool:
        """Atomically reinject an event into its stream, remove it from the DLQ, and bump the
        match's retry count (refreshing its TTL)."""
        match_id = record.original_data.match_id
        target_stream = record.original_stream
        payload = record.original_data.payload
        count_key = self._count_key(retry_key)

        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                await self.redis_service._publish_event(pipe, target_stream, match_id, payload)
                pipe.hdel(dlq_hash_name, record.original_event_id)
                pipe.incr(count_key)
                pipe.expire(count_key, DLQ_RETRY_COUNT_TTL_SECONDS)
                await pipe.execute()

            retry_count = await self._get_retry_count(retry_key)
            logger.info(
                f"DLQ: reinjected match {match_id} into '{target_stream}' " f"(retry {retry_count}/{self.max_retries})"
            )
            return True
        except Exception as e:
            logger.error(f"DLQ: failed to reinject match {match_id} into '{target_stream}': {e}", exc_info=True)
            return False
