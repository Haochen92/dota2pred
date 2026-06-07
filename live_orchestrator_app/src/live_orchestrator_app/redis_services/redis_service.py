import redis.asyncio as redis
from redis.asyncio.client import Pipeline
import asyncio
import json
import logging
import os
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.time_utils import get_current_utc_iso_timestamp, convert_redis_timestamp
from typing import Awaitable, Callable, List, Set, Type, Tuple, Dict
from pydantic import ValidationError, BaseModel
from datetime import timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, after_log

from dota_oracle_common.models.redis.schema import (
    MatchProcessingStatus,
    MatchStatusValue,
    EventToPublish,
    ConsumedEvent,
    FailureRecord,
    FeatureEngineeringPayload,
    PredictionPayload,
    CompletionPayload,
    PayloadModel,
)
from dota_oracle_common.models.match import MatchTable

# Constants
from dota_oracle_common.constants.redis_constants import (
    MATCH_SET,
    MATCH_STATUS,
    TMP_KEY,
    STREAM_NEW_MATCHES,
    STREAM_PENDING_PREDICTION,
    STREAM_PENDING_COMPLETION,
    FEATURE_ENGINEER_GROUP,
    PREDICTION_GROUP,
    COMPLETION_GROUP,
    FAILED_EVENTS_MAPPING,
)

logger = get_logger(__name__)

# Backstop cap so the streams can't grow unbounded (pending_completion had reached ~69k
# entries since Aug 2025 because completed events were ACKed but never deleted). Approximate
# trimming (~) is cheap; with XDEL-on-complete the stream normally stays far below this.
STREAM_MAXLEN = int(os.getenv("REDIS_STREAM_MAXLEN", "50000"))

# match_status:{id} hashes are deleted on completion/discard, but paths without an explicit
# delete (earlier-stage failures, completion DLQ) would leak them (they had no TTL -> ~2,888
# accumulated). A TTL refreshed on every stage transition is a self-cleaning safety net: an
# in-flight match (<=2h lifecycle) always refreshes it long before expiry, while an abandoned
# one disappears on its own. Set above the 2h completion age-out with margin.
MATCH_STATUS_TTL_SECONDS = int(os.getenv("MATCH_STATUS_TTL_SECONDS", str(6 * 3600)))

DecodedStreamResponse = List[Tuple[str, List[Tuple[str, Dict[str, str]]]]]


class RedisService:
    def __init__(self, redis_client: redis.Redis):
        # Expects an asyncio Redis client.
        self.redis: redis.Redis = redis_client
        self._initialized: bool = False

    @classmethod
    async def create(cls, redis_client: redis.Redis) -> "RedisService":
        # A class method which initialises the class with injected dependenceis
        instance = cls(redis_client=redis_client)
        await instance.initialize_async_service()
        return instance

    async def initialize_async_service(self) -> None:
        if self._initialized:
            return

        logger.info("Initializing RedisService: Ensuring consumer groups exist...")
        await asyncio.gather(
            self._create_group(STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP),
            self._create_group(STREAM_PENDING_PREDICTION, PREDICTION_GROUP),
            self._create_group(STREAM_PENDING_COMPLETION, COMPLETION_GROUP),
        )
        self._initialized = True
        logger.info("RedisService initialized.")

    async def _create_group(self, stream: str, group: str) -> None:
        """Creates a consumer group if it doesn't exist. Idempotent."""
        try:
            # Use "0" to read all messages from the beginning (important for tests)
            await self.redis.xgroup_create(stream, group, id="0", mkstream=True)
            logger.info(f"Created/confirmed consumer group '{group}' for stream '{stream}'")
        except redis.ResponseError as e:
            if "BUSYGROUP Consumer Group name already exists" in str(e):
                logger.info(f"Consumer group '{group}' already exists for stream '{stream}'.")
            else:
                logger.error(f"Error creating/checking group '{group}' for stream '{stream}': {e}", exc_info=True)
                raise

    """
    Generic Helper Functions
    """

    @retry(
        retry=retry_if_exception_type((redis.ConnectionError, redis.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        after=after_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _run_transaction_with_retry(self, build: Callable[[Pipeline], Awaitable[None]]) -> None:
        """Run a transactional pipeline, retrying on transient Redis connection errors.

        ``build`` populates the pipeline (status hset, xadd, xack, ...). The whole
        transaction is rebuilt and re-executed on each attempt so a dropped connection
        can't leave a half-built pipeline. After the retries are exhausted the last
        error propagates to the caller, which decides how to surface it.
        """
        async with self.redis.pipeline(transaction=True) as pipe:
            await build(pipe)
            await pipe.execute()

    async def _publish_event(self, pipe: Pipeline, stream_name: str, match_id: int, payload: BaseModel) -> None:
        """
        Generic helper to construct, serialize, and add an event to a stream
        within a Redis pipeline transaction.
        """
        # 1. Create the specific event envelope using the provided payload
        EventModel = EventToPublish[type(payload)]
        event_to_publish = EventModel(match_id=match_id, payload=payload)

        payload_json = payload.model_dump_json()
        event_json = event_to_publish.model_dump(mode="json")

        event_json["payload"] = payload_json

        # 3. Add the XADD command to the pipeline (capped so the stream can't grow unbounded)
        pipe.xadd(stream_name, event_json, maxlen=STREAM_MAXLEN, approximate=True)  # type: ignore

    async def _fetch_events(
        self, group: str, consumer: str, stream: str, payload_model: Type[PayloadModel], batch: int
    ) -> List[ConsumedEvent[PayloadModel]]:
        """
        Generic helper to fetch and parse events from a stream for a given payload type.
        """

        try:
            all_events = []

            # Step 1: Try to read from this consumer's own Pending Entries List (PEL).
            pending_events_response = await self.redis.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: "0"},  # Read pending unacknowledged messages
                count=batch,
            )

            if pending_events_response and pending_events_response[0][1]:
                all_events.extend(pending_events_response[0][1])

            # STEP 2: Read new messages (always try, regardless of pending messages)
            remaining_batch = max(0, batch - len(all_events))
            if remaining_batch > 0:
                new_events_response = await self.redis.xreadgroup(
                    groupname=group,
                    consumername=consumer,
                    streams={stream: ">"},  # Read new messages
                    count=remaining_batch,
                    block=1000,  # 1 second timeout
                )

                if new_events_response and new_events_response[0][1]:
                    all_events.extend(new_events_response[0][1])

            if not all_events:
                return []

            return self._parse_raw_events(all_events, payload_model)
        except redis.TimeoutError:
            return []
        except Exception as e:
            logger.error(f"Critical Error reading and parsing stream {stream} for group {group}: {e}", exc_info=True)
            raise

    def _parse_raw_events(
        self, raw_events: List[Tuple[str, Dict[str, str]]], payload_model: Type[PayloadModel]
    ) -> List[ConsumedEvent[PayloadModel]]:
        """
        A private helper to parse a raw list of event data from Redis
        into a list of validated ConsumedEvent Pydantic models.
        """
        parsed_events: List[ConsumedEvent[PayloadModel]] = []
        ExpectedEventModel = ConsumedEvent[payload_model]

        for event_id, data_dict in raw_events:
            try:
                # This is your shared logic
                payload_json = data_dict.get("payload")
                if not payload_json:
                    logger.warning(f"Event {event_id} is missing a payload. Skipping.")
                    continue

                parsed_payload = payload_model.model_validate_json(payload_json)

                final_event_data = {
                    "event_id": event_id,
                    "timestamp": data_dict.get("timestamp"),
                    "match_id": data_dict.get("match_id"),
                    "payload": parsed_payload,
                }
                consumed_event = ExpectedEventModel.model_validate(final_event_data)
                parsed_events.append(consumed_event)
            except ValidationError as ve:
                logger.warning(f"Pydantic validation failed for event ID '{event_id}'. Error: {ve}")
                continue
            except Exception as e:
                # Log the error but continue processing the rest of the batch
                logger.error(f"Critical error parsing event ID '{event_id}': {e}", exc_info=True)
                continue  # Important to not let one bad event stop the whole batch

        return parsed_events

    # ============================================
    #   Stage 1: New Match -> Feature Engineering
    # ============================================

    # New match orchestrator
    async def update_live_match_set_and_get_new(self, curr_ids: List[int]) -> Set[int]:
        """Updates tracked set atomically using RENAME, returns new IDs."""
        new_match_ids: Set[int] = set()
        curr_ids_str = [str(id) for id in curr_ids]
        try:
            await self.redis.delete(TMP_KEY)
            if curr_ids_str:
                await self.redis.sadd(TMP_KEY, *curr_ids_str)  # type: ignore

            new_ids_raw = await self.redis.sdiff(TMP_KEY, MATCH_SET)  # type: ignore
            new_match_ids = {int(id_str) for id_str in new_ids_raw}
            await self.redis.rename(TMP_KEY, MATCH_SET)
            logger.info(f"Updated live match set. Found {len(new_match_ids)} new matches.")
        except Exception as e:
            logger.error(f"Failed to update live match set: {e}", exc_info=True)
            await self.redis.delete(TMP_KEY)
            return set()
        return new_match_ids

    async def publish_new_match_to_feature_eng(self, match_details: MatchTable) -> bool:
        """
        Takes a MatchTable object, constructs the event, and adds it to the feature engineering stream.
        """
        match_id = match_details.match_id

        try:
            payload = FeatureEngineeringPayload(match_details=match_details)

            async def _build(pipe: Pipeline) -> None:
                # Set initial status (with a refreshed TTL so an abandoned status self-cleans)
                status_model = MatchStatusValue(status=MatchProcessingStatus.NEW)
                pipe.hset(f"{MATCH_STATUS}:{match_id}", mapping=status_model.model_dump())
                pipe.expire(f"{MATCH_STATUS}:{match_id}", MATCH_STATUS_TTL_SECONDS)

                # Publish event message to stream
                await self._publish_event(pipe, STREAM_NEW_MATCHES, match_id, payload)

            await self._run_transaction_with_retry(_build)

            logger.info(f"Published match {match_id} to stream '{STREAM_NEW_MATCHES}'")
            return True
        except Exception as e:
            logger.error(f"Failed publishing match {match_id} to stream {STREAM_NEW_MATCHES}: {e}", exc_info=True)
            return False

    # Feature engineering stage
    async def fetch_new_matches_for_feature_eng(
        self, consumer: str, count: int = 50
    ) -> List[ConsumedEvent[FeatureEngineeringPayload]]:
        """Fetches events from the new matches stream with the expected payload."""
        return await self._fetch_events(
            FEATURE_ENGINEER_GROUP, consumer, STREAM_NEW_MATCHES, FeatureEngineeringPayload, count
        )

    async def publish_features_to_prediction(
        self, match_id: int, features: PredictionPayload, event_id_to_ack: str
    ) -> bool:
        """
        Publishes engineered features to the prediction stream and ACKs the previous event.
        """

        try:

            async def _build(pipe: Pipeline) -> None:
                # 1. Set the status for this specific stage (refresh the TTL)
                status_model = MatchStatusValue(status=MatchProcessingStatus.PENDING_PREDICTION)
                pipe.hset(f"{MATCH_STATUS}:{match_id}", mapping=status_model.model_dump())
                pipe.expire(f"{MATCH_STATUS}:{match_id}", MATCH_STATUS_TTL_SECONDS)

                # 2. Call the generic helper
                await self._publish_event(pipe, STREAM_PENDING_PREDICTION, match_id, features)

                # 3. Add the ACK command for this specific stage transition
                pipe.xack(STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP, event_id_to_ack)

            await self._run_transaction_with_retry(_build)

            logger.info(f"Advanced match {match_id} to stream '{STREAM_PENDING_PREDICTION}'")
            return True
        except Exception as e:
            logger.error(f"Redis failure advancing match {match_id} to pending prediction: {e}", exc_info=True)
            return False

    # Prediction stage
    async def fetch_matches_for_prediction(
        self, consumer: str, count: int = 50
    ) -> List[ConsumedEvent[PredictionPayload]]:
        """Fetches events from the pending prediction stream with the expected payload."""
        return await self._fetch_events(PREDICTION_GROUP, consumer, STREAM_PENDING_PREDICTION, PredictionPayload, count)

    async def publish_prediction_to_completion(
        self, match_id: int, prediction: CompletionPayload, event_id_to_ack: str
    ) -> bool:
        """
        Publishes a prediction result to the completion stream and ACKs the
        message from the prediction stream.
        """
        try:

            async def _build(pipe: Pipeline) -> None:
                # 1. Set the status for this stage (refresh the TTL)
                status_model = MatchStatusValue(status=MatchProcessingStatus.PENDING_COMPLETION)
                pipe.hset(f"{MATCH_STATUS}:{match_id}", mapping=status_model.model_dump())
                pipe.expire(f"{MATCH_STATUS}:{match_id}", MATCH_STATUS_TTL_SECONDS)

                # 2. Call the generic helper to publish the event
                await self._publish_event(pipe, STREAM_PENDING_COMPLETION, match_id, prediction)

                # 3. ACK the message from the previous (prediction) stream
                pipe.xack(STREAM_PENDING_PREDICTION, PREDICTION_GROUP, event_id_to_ack)

            await self._run_transaction_with_retry(_build)

            logger.info(f"Advanced match {match_id} to stream '{STREAM_PENDING_COMPLETION}'")
            return True
        except Exception as e:
            logger.error(f"Redis failure advancing match {match_id} to pending completion: {e}", exc_info=True)
            return False

    async def fetch_matches_for_completion(
        self, consumer: str, count: int = 50
    ) -> List[ConsumedEvent[CompletionPayload]]:
        """
        Fetches events from the pending completion stream with the expected payload.
        """
        return await self._fetch_events(COMPLETION_GROUP, consumer, STREAM_PENDING_COMPLETION, CompletionPayload, count)

    async def mark_match_as_completed(self, match_id: int, event_id_to_ack: str) -> bool:
        """Atomically deletes status hash and ACKs the final processing stream event."""
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.delete(f"{MATCH_STATUS}:{match_id}")
                pipe.xack(STREAM_PENDING_COMPLETION, COMPLETION_GROUP, event_id_to_ack)
                # Delete the entry too: ACK alone leaves it in the stream forever (the source
                # of the ~69k backlog). XDEL keeps the stream bounded to in-flight work.
                pipe.xdel(STREAM_PENDING_COMPLETION, event_id_to_ack)
                await pipe.execute()
            return True
        except Exception as e:
            logger.error(
                f"Redis failure marking match {match_id} as completed (ACK ID: {event_id_to_ack}): {e}", exc_info=True
            )
            return False

    async def discard_unresolvable_event(
        self,
        match_id: int,
        event_id: str,
        consumer_group: str,
        event_stream: str,
        reason: str,
    ) -> None:
        """Terminally drop a pending event we've decided will never resolve.

        Unlike handle_processing_failure (which routes to the retryable DLQ and gets
        re-injected by the DLQ sweep), this ACKs *and* XDELs the entry so it leaves the
        pipeline for good. A match's outcome, if it's ever real, still arrives via the
        separate proMatches -> DB batch backfill.
        """
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.xack(event_stream, consumer_group, event_id)
                pipe.xdel(event_stream, event_id)
                # Don't leak the status hash for a match we're giving up on.
                pipe.delete(f"{MATCH_STATUS}:{match_id}")
                await pipe.execute()
            logger.warning(
                f"Discarded unresolvable match {match_id} (event {event_id}) from '{event_stream}': {reason}"
            )
        except Exception as e:
            logger.error(f"Failed to discard unresolvable match {match_id} (event {event_id}): {e}", exc_info=True)

    # =======================================================
    # Failure Events Management
    # =======================================================

    async def handle_processing_failure(
        self,
        event_data: ConsumedEvent,
        event_id: str,
        error: Exception,
        consumer_group: str,
        event_stream: str,
    ) -> None:
        """Handles processing failures by recording them in Redis."""
        try:
            failure_record = FailureRecord(
                original_group=consumer_group,
                original_event_id=event_id,
                original_data=event_data,
                original_stream=event_stream,
                error_type=type(error).__name__,
                error_message=str(error),
                failure_timestamp=get_current_utc_iso_timestamp(),
            )

            await self._record_failure_and_ack(failure_record)

            logger.info(f"Recorded failure for event '{event_id}'")

        except Exception as e:
            logger.error(f"Failed to record failure for event '{event_id}': {e}", exc_info=True)

    async def _record_failure_and_ack(self, failure_record: FailureRecord) -> bool:
        """
        Records failure details to DLQ Hash and ACKs original message.
        Simplifies serialization error handling.
        """
        target_hash = FAILED_EVENTS_MAPPING.get(failure_record.original_stream)
        if not target_hash:
            logger.error(
                f"Unknown stream '{failure_record.original_stream}' in FAILED_EVENTS_MAPPING."
                f"Cannot record failure or ACK event {failure_record.original_event_id}."
            )
            return False

        try:
            failure_json = failure_record.model_dump_json()
        except Exception as e:
            # If serialization fails for any reason, log it and create a minimal JSON payload
            logger.error(
                f"Failed to serialize failure data for event {failure_record.original_event_id} "
                f"from stream '{failure_record.original_stream}'. "
                f"Storing minimal failure info. Serialization error: {e}",
                exc_info=True,
            )
            # Create a minimal JSON payload with essential info from the failure_record
            failure_json = json.dumps(
                {
                    "error": "DLQ data serialization failed",
                    "original_event_id": failure_record.original_event_id,
                    "original_stream": failure_record.original_stream,
                    "error_type": type(e).__name__,
                    "error_message": f"Original serialization failed: {e}",
                    "failure_timestamp": failure_record.failure_timestamp.isoformat(),
                }
            )

        # Attempt to record failure in Redis and ACK the original message
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                # Store the JSON string in the DLQ hash
                pipe.hset(target_hash, failure_record.original_event_id, failure_json)
                # ACK the original message in the stream
                pipe.xack(
                    failure_record.original_stream, failure_record.original_group, failure_record.original_event_id
                )
                await pipe.execute()

            logger.warning(
                f"Recorded failure for event {failure_record.original_event_id} "
                f"from stream '{failure_record.original_stream}' "
                f"to hash '{target_hash}' and ACKed original message."
            )
            return True

        except Exception as e:
            # This is a critical error: we failed to record the failure AND ACK
            logger.critical(
                f"CRITICAL: Failed to record failure AND ACK original event {failure_record.original_event_id} "
                f"from stream '{failure_record.original_stream}'. Message may remain pending/cause blocking. "
                f"Hash target: '{target_hash}'. Redis error: {e}",
                exc_info=True,
            )
            return False

    async def fetch_expired_events(
        self,
        stream_name: str,
        consumer_group: str,
        duration: int,
    ) -> List[str]:
        pending_events_list = await self.redis.xpending_range(
            name=stream_name, groupname=consumer_group, min="-", max="+", count=1000
        )

        expired_events_list: List[str] = []
        expiry_duration = timedelta(seconds=duration)
        curr_datetime = get_current_utc_iso_timestamp()

        for event in pending_events_list:
            event_id: str = event["message_id"]
            start_datetime = convert_redis_timestamp(event_id)

            pending_duration = curr_datetime - start_datetime
            if pending_duration > expiry_duration:
                expired_events_list.append(event_id)

        logger.info(f"Found {len(expired_events_list)} expired events in {stream_name}, {consumer_group}")
        return expired_events_list

    async def claim_expired_events(
        self,
        events_id_list: List[str],
        stream_name: str,
        consumer_group: str,
        consumer_name: str,
        payload_model: Type[PayloadModel],
    ) -> List[ConsumedEvent[PayloadModel]]:

        if not events_id_list:
            logger.warning("events_id_list is empty, returning...")
            return []

        claimed_events = await self.redis.xclaim(
            name=stream_name,
            groupname=consumer_group,
            consumername=consumer_name,
            message_ids=events_id_list,  # type: ignore
            min_idle_time=0,
        )

        if not claimed_events:
            return []

        return self._parse_raw_events(claimed_events, payload_model)

    # --- Live Tracking / Dashboard Features ---
    async def get_live_match_ids(self) -> Set[int]:
        """Gets current live match IDs from the set."""
        try:
            ids_raw = await self.redis.smembers(MATCH_SET)  # type: ignore
            if not ids_raw:
                return set()

            return {int(id_str) for id_str in ids_raw}
        except Exception as e:
            logger.error(f"Failed getting live match IDs: {e}", exc_info=True)
            return set()
