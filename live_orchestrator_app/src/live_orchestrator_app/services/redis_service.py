import redis.asyncio as redis
from redis.asyncio.client import Pipeline
import asyncio
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.time_utils import get_current_utc_iso_timestamp
from typing import List, Set, Type
from pydantic import ValidationError, BaseModel

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
import json

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

    async def _fetch_events(
        self, group: str, consumer: str, stream: str, payload_model: Type[PayloadModel], batch: int
    ) -> List[ConsumedEvent[PayloadModel]]:
        """
        Generic helper to fetch and parse events from a stream for a given payload type.
        """

        try:
            # Step 1: Try to read from this consumer's own Pending Entries List (PEL).
            raw_events_response = await self.redis.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: "0"},  # Read pending unacknowledged messages
                count=batch,
            )

            # STEP 2: No pending messages - poll for new ones
            if not raw_events_response:
                raw_events_response = await self.redis.xreadgroup(
                    groupname=group,
                    consumername=consumer,
                    streams={stream: ">"},  # Read new messages
                    count=batch,
                    block=1000,
                )

            if not raw_events_response:
                return []

            _stream_name_bytes, events_list = raw_events_response[0]

            parsed_events: List[ConsumedEvent[PayloadModel]] = []  # Create type hint for generic return type

            ExpectedEventModel = ConsumedEvent[payload_model]  # Create the specific instance of ConsumedEvent

            for event_id, data_dict in events_list:
                try:
                    data_dict[event_id] = event_id  # fill in event_id
                    parsed_event = ExpectedEventModel.model_validate(data_dict)
                    parsed_events.append(parsed_event)
                except ValidationError as ve:
                    logger.warning(
                        f"Pydantic validation failed for event ID '{event_id}' from stream '{stream}'. Error: {ve} "
                    )
                    continue
            return parsed_events
        except redis.TimeoutError:
            return []
        except Exception as e:
            logger.error(f"Critical Error reading and parsing stream {stream} for group {group}: {e}", exc_info=True)
            raise

    async def _publish_event(self, pipe: Pipeline, stream_name: str, match_id: int, payload: BaseModel) -> None:
        """
        Generic helper to construct, serialize, and add an event to a stream
        within a Redis pipeline transaction.
        """
        # 1. Create the specific event envelope using the provided payload
        EventModel = EventToPublish[payload]
        event_to_publish = EventModel(match_id=match_id, payload=payload)

        # 2. Serialize and flatten the event for Redis
        event_dict = event_to_publish.model_dump(mode="json")
        flat_event_data = {key: str(value) for key, value in event_dict.items()}

        # 3. Add the XADD command to the pipeline
        pipe.xadd(stream_name, flat_event_data)  # type: ignore

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

            async with self.redis.pipeline(transaction=True) as pipe:
                # Set initial status
                status_model = MatchStatusValue(status=MatchProcessingStatus.NEW)
                pipe.hset(f"{MATCH_STATUS}:{match_id}", mapping=status_model.model_dump())

                # Publish event message to stream
                await self._publish_event(pipe, STREAM_NEW_MATCHES, match_id, payload)

                # Execute Transaction
                await pipe.execute()

            logger.info(f"Published match {match_id} to stream '{STREAM_NEW_MATCHES}'")
            return True
        except Exception as e:
            logger.error(f"Failed publishing match {match_id} to stream {STREAM_NEW_MATCHES}: {e}", exc_info=True)
            return False

    # Feature engineering stage
    async def fetch_new_matches_for_feature_eng(
        self, consumer: str, count: int = 10
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
            async with self.redis.pipeline(transaction=True) as pipe:
                # 1. Set the status for this specific stage
                status_model = MatchStatusValue(status=MatchProcessingStatus.PENDING_PREDICTION)
                pipe.hset(f"{MATCH_STATUS}:{match_id}", mapping=status_model.model_dump())

                # 2. Call the generic helper
                await self._publish_event(pipe, STREAM_PENDING_PREDICTION, match_id, features)

                # 3. Add the ACK command for this specific stage transition
                pipe.xack(STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP, event_id_to_ack)

                # 4. Execute the transaction
                await pipe.execute()

            logger.info(f"Advanced match {match_id} to stream '{STREAM_PENDING_PREDICTION}'")
            return True
        except Exception as e:
            logger.error(f"Redis failure advancing match {match_id} to pending prediction: {e}", exc_info=True)
            return False

    # Prediction stage
    async def fetch_matches_for_prediction(
        self, consumer: str, count: int = 10
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
            async with self.redis.pipeline(transaction=True) as pipe:
                # 1. Set the status for this stage
                status_model = MatchStatusValue(status=MatchProcessingStatus.PENDING_COMPLETION)
                pipe.hset(f"{MATCH_STATUS}:{match_id}", mapping=status_model.model_dump())

                # 2. Call the generic helper to publish the event
                await self._publish_event(pipe, STREAM_PENDING_COMPLETION, match_id, prediction)

                # 3. ACK the message from the previous (prediction) stream
                pipe.xack(STREAM_PENDING_PREDICTION, PREDICTION_GROUP, event_id_to_ack)

                # 4. Execute the transaction
                await pipe.execute()

            logger.info(f"Advanced match {match_id} to stream '{STREAM_PENDING_COMPLETION}'")
            return True
        except Exception as e:
            logger.error(f"Redis failure advancing match {match_id} to pending completion: {e}", exc_info=True)
            return False

    async def fetch_matches_for_completion(
        self, consumer: str, count: int = 20
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
                await pipe.execute()
            return True
        except Exception as e:
            logger.error(
                f"Redis failure marking match {match_id} as completed (ACK ID: {event_id_to_ack}): {e}", exc_info=True
            )
            return False

    # Failed Events management

    async def handle_processing_failure(
        self,
        event_data: ConsumedEvent[PayloadModel],
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
