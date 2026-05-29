import json
from typing import Optional

from dota_oracle_common.constants.redis_constants import FAILED_EVENTS_MAPPING, DLQ_RETRY_COUNTS_HASH
from dota_oracle_common.models.redis.schema import FailureRecord
from dota_oracle_common.utils.set_logging import get_logger
from ..constants.payload_mappings import PAYLOAD_MODEL_MAPPING
from ..redis_services.redis_service import RedisService

logger = get_logger(__name__)


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
        raw_events = await self.redis.hgetall(dlq_hash_name)
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
                logger.warning(
                    f"DLQ: match {match_id} in '{stream_name}' exhausted {self.max_retries} retries, skipping"
                )
                continue

            success = await self._reinject_event(record, dlq_hash_name, retry_key)
            if success:
                reinjected += 1

        await self._cleanup_stale_counts(stream_name, dlq_hash_name)
        return reinjected

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
        """Get the current retry count for a match from the retry tracking hash."""
        count = await self.redis.hget(DLQ_RETRY_COUNTS_HASH, retry_key)
        return int(count) if count else 0

    async def _reinject_event(self, record: FailureRecord, dlq_hash_name: str, retry_key: str) -> bool:
        """Atomically reinject an event into its stream, remove from DLQ, and increment retry count."""
        match_id = record.original_data.match_id
        target_stream = record.original_stream
        payload = record.original_data.payload

        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                await self.redis_service._publish_event(pipe, target_stream, match_id, payload)
                pipe.hdel(dlq_hash_name, record.original_event_id)
                pipe.hincrby(DLQ_RETRY_COUNTS_HASH, retry_key, 1)
                await pipe.execute()

            retry_count = await self._get_retry_count(retry_key)
            logger.info(
                f"DLQ: reinjected match {match_id} into '{target_stream}' " f"(retry {retry_count}/{self.max_retries})"
            )
            return True
        except Exception as e:
            logger.error(f"DLQ: failed to reinject match {match_id} into '{target_stream}': {e}", exc_info=True)
            return False

    async def _cleanup_stale_counts(self, stream_name: str, dlq_hash_name: str) -> None:
        """Remove retry counts for matches no longer in this DLQ hash."""
        all_counts = await self.redis.hgetall(DLQ_RETRY_COUNTS_HASH)
        if not all_counts:
            return

        dlq_events = await self.redis.hgetall(dlq_hash_name)
        dlq_match_ids = set()
        for event_json in dlq_events.values():
            try:
                raw = json.loads(event_json)
                dlq_match_ids.add(str(raw.get("original_data", {}).get("match_id", "")))
            except Exception:
                continue

        prefix = f"{stream_name}:"
        stale_keys = []
        for retry_key in all_counts:
            if not retry_key.startswith(prefix):
                continue
            match_id = retry_key[len(prefix) :]
            if match_id not in dlq_match_ids:
                stale_keys.append(retry_key)

        if stale_keys:
            await self.redis.hdel(DLQ_RETRY_COUNTS_HASH, *stale_keys)
            logger.debug(f"DLQ: cleaned up {len(stale_keys)} stale retry counts for '{stream_name}'")
