import redis.asyncio as redis
import asyncio
from dota_oracle.utils.set_logging import get_logger
from dota_oracle.utils.time_utils import get_current_utc_iso_timestamp
from typing import List, Dict, Set
from pydantic import ValidationError
from dota_oracle.pydantic_models.redis_models import MatchProcessingStatus, MatchStatusValue, StreamMatchEventData, FailureRecord
import json

# Constants
from dota_oracle.constants.redis_constants import (
    MATCH_SET, MATCH_STATUS, TMP_KEY,
    STREAM_NEW_MATCHES, STREAM_PENDING_PREDICTION, STREAM_PENDING_COMPLETION, 
    FEATURE_ENGINEER_GROUP, PREDICTION_GROUP, COMPLETION_GROUP,
    FAILED_EVENTS_MAPPING
)

logger = get_logger(__name__)

class RedisService:
    def __init__(self, redis_client: redis.Redis):
        # Expects an asyncio Redis client.
        self.redis: redis.Redis = redis_client
        self._initialized:bool = False

    async def initialize(self):
        if self._initialized:
            return

        logger.info("Initializing RedisService: Ensuring consumer groups exist...")
        await asyncio.gather(
             self._create_group(STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP),
             self._create_group(STREAM_PENDING_PREDICTION, PREDICTION_GROUP),
             self._create_group(STREAM_PENDING_COMPLETION, COMPLETION_GROUP)
        )
        self._initialized = True
        logger.info("RedisService initialized.")

    async def _create_group(self, stream:str, group:str) -> None:
        """Creates a consumer group if it doesn't exist. Idempotent."""
        try:
            await self.redis.xgroup_create(stream, group, id='0', mkstream=True)
            logger.info(f"Created/confirmed consumer group '{group}' for stream '{stream}'")
        except redis.ResponseError as e:
            if 'BUSYGROUP Consumer Group name already exists' in str(e):
                logger.info(f"Consumer group '{group}' already exists for stream '{stream}'.")
            else:
                logger.error(f"Error creating/checking group '{group}' for stream '{stream}': {e}", exc_info=True)
                raise

    '''
    Helper Functions
    '''
    async def _fetch_events( self, group: str, consumer: str, stream: str, batch: int) -> Dict[str, StreamMatchEventData]: 
        """
        Fetches batch of events, parses them into StreamMatchEventData models,
        returns dict {event_id: StreamMatchEventData_instance}.
        """
        parsed_events: Dict[str, StreamMatchEventData] = {}
        try:
            raw_events_response = await self.redis.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: '>'},
                count=batch,
                block=1000
            )
            if not raw_events_response:
                return {}

            _stream_name, stream_events_data_list = raw_events_response[0]

            for event_id, data_dict in stream_events_data_list:
                try:
                    parsed_event = StreamMatchEventData.model_validate(data_dict)
                    parsed_events[event_id] = parsed_event
                except ValidationError as e:
                    logger.warning(
                        f"Pydantic validation failed for event ID '{event_id}' from stream '{stream}'. "
                    )
                    continue
            return parsed_events
        except redis.TimeoutError:
            return {} 
        except Exception as e:
            logger.error(f"Error reading and parsing stream {stream} for group {group}: {e}", exc_info=True)
            return {}

    # New match orchestrator
    async def update_live_match_set_and_get_new(self, curr_ids: List[int]) -> Set[int]:
        """Updates tracked set atomically using RENAME, returns new IDs."""
        new_match_ids: Set[int] = set()
        curr_ids_str = [str(id) for id in curr_ids]
        try:
            await self.redis.delete(TMP_KEY)
            if curr_ids_str:
                await self.redis.sadd(TMP_KEY, *curr_ids_str) # type: ignore

            new_ids_raw = await self.redis.sdiff(TMP_KEY, MATCH_SET) # type: ignore
            new_match_ids = {int(id_str) for id_str in new_ids_raw}
            await self.redis.rename(TMP_KEY, MATCH_SET)
            logger.info(f"Updated live match set. Found {len(new_match_ids)} new matches.")
        except Exception as e:
            logger.error(f"Failed to update live match set: {e}", exc_info=True)
            await self.redis.delete(TMP_KEY)
            return set()
        return new_match_ids

    async def add_match_for_processing(self, match_id: int) -> bool:
        """Atomically sets initial status and adds match to the first stream."""
        if not match_id or type(match_id) != int:
            logger.error(f"Missing input value or invalid datatype")
            return False
        match_id_str = str(match_id)
        timestamp = get_current_utc_iso_timestamp()
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                status_model = MatchStatusValue(status=MatchProcessingStatus.NEW)
                pipe.hset(f'{MATCH_STATUS}:{match_id_str}', mapping=status_model.model_dump())
                
                # Using StreamMatchEventData to construct payload for xadd
                event_data_model = StreamMatchEventData(match_id=match_id, timestamp=timestamp) 
                pipe.xadd(STREAM_NEW_MATCHES, event_data_model.model_dump()) # type: ignore
                await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Failed adding match {match_id} to stream {STREAM_NEW_MATCHES}: {e}", exc_info=True)
            return False

    # Feature engineering stage
    async def fetch_new_matches_for_feature_eng(self, consumer: str, count: int=10) -> Dict[str, StreamMatchEventData]: 
        """Fetches events from the new matches stream, parsed into Pydantic models."""
        return await self._fetch_events(FEATURE_ENGINEER_GROUP, consumer, STREAM_NEW_MATCHES, count)

    async def advance_match_to_pending_prediction(self, match_id: int, event_id_to_ack: str) -> bool:
        """Atomically updates status, adds to next stream, ACKs previous stream event."""
        if not match_id or type(match_id) != int:
            logger.error(f"match_id {match_id} has invalid type {type(match_id)} or missing")
            return False
        elif not event_id_to_ack:
            logger.error(f"event_id cannot be missing")
            return False  
        
        match_id_str = str(match_id)
        timestamp = get_current_utc_iso_timestamp()
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                status_model = MatchStatusValue(status=MatchProcessingStatus.PENDING_PREDICTION)
                pipe.hset(f'{MATCH_STATUS}:{match_id_str}', mapping=status_model.model_dump())

                event_data_model = StreamMatchEventData(match_id=match_id, timestamp=timestamp)
                pipe.xadd(STREAM_PENDING_PREDICTION, event_data_model.model_dump()) # type: ignore
                pipe.xack(STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP, event_id_to_ack)
                await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Redis failure advancing match {match_id} to pending prediction (ACK ID: {event_id_to_ack}): {e}", exc_info=True)
            return False

    # Prediction stage
    async def fetch_matches_pending_prediction(self, consumer: str, count: int=10) -> Dict[str, StreamMatchEventData]:
        """Fetches events from the pending prediction stream, parsed into Pydantic models."""
        return await self._fetch_events(PREDICTION_GROUP, consumer, STREAM_PENDING_PREDICTION, count)

    async def advance_match_to_pending_completion(self, match_id: int, event_id_to_ack: str) -> bool:
        """Atomically updates status, adds to next stream, ACKs previous stream event."""
        if not match_id or type(match_id) != int:
            logger.error(f"match_id {match_id} has invalid type {type(match_id)} or missing")
            return False
        elif not event_id_to_ack:
            logger.error(f"event_id cannot be missing")
            return False 
        
        match_id_str = str(match_id)
        timestamp = get_current_utc_iso_timestamp()
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                status_model = MatchStatusValue(status=MatchProcessingStatus.PENDING_COMPLETION)
                pipe.hset(f'{MATCH_STATUS}:{match_id_str}', mapping=status_model.model_dump())

                event_data_model = StreamMatchEventData(match_id=match_id, timestamp=timestamp)
                pipe.xadd(STREAM_PENDING_COMPLETION, event_data_model.model_dump()) # type: ignore
                pipe.xack(STREAM_PENDING_PREDICTION, PREDICTION_GROUP, event_id_to_ack)
                await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Redis failure advancing match {match_id} to pending completion (ACK ID: {event_id_to_ack}): {e}", exc_info=True)
            return False

    # --- PENDING COMPLETION STAGE ---
    async def fetch_matches_pending_completion(self, consumer: str, count: int=20) -> Dict[str, StreamMatchEventData]: # MODIFIED RETURN TYPE
        """Fetches events from the pending completion stream, parsed into Pydantic models."""
        return await self._fetch_events(COMPLETION_GROUP, consumer, STREAM_PENDING_COMPLETION, count)

    async def mark_match_as_completed(self, match_id: int, event_id_to_ack: str) -> bool:
        """Atomically deletes status hash and ACKs the final processing stream event."""
        if not match_id or type(match_id) != int:
            logger.error(f"match_id {match_id} has invalid type {type(match_id)} or missing")
            return False
        elif not event_id_to_ack:
            logger.error(f"event_id cannot be missing")
            return False 
        
        match_id_str = str(match_id)
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.delete(f'{MATCH_STATUS}:{match_id_str}')
                pipe.xack(STREAM_PENDING_COMPLETION, COMPLETION_GROUP, event_id_to_ack)
                await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Redis failure marking match {match_id} as completed (ACK ID: {event_id_to_ack}): {e}", exc_info=True)
            return False

    # Failed Events management
    async def record_failure_and_ack(self, failure_record: FailureRecord) -> bool:
        """
        Records failure details to DLQ Hash and ACKs original message.
        Simplifies serialization error handling.
        """
        target_hash = FAILED_EVENTS_MAPPING.get(failure_record.original_stream)
        if not target_hash:
            logger.error(f"Unknown stream '{failure_record.original_stream}' in FAILED_EVENTS_MAPPING." 
                         f"Cannot record failure or ACK event {failure_record.original_event_id}.")
            return False

        try:
            failure_json = failure_record.model_dump_json()
        except Exception as e:
        # If serialization fails for any reason, log it and create a minimal JSON payload
            logger.error(
                f"Failed to serialize failure data for event {failure_record.original_event_id} "
                f"from stream '{failure_record.original_stream}'. "
                f"Storing minimal failure info. Serialization error: {e}",
                exc_info=True 
            )
            # Create a minimal JSON payload with essential info from the failure_record
            failure_json = json.dumps({
                "error": "DLQ data serialization failed",
                "original_event_id": failure_record.original_event_id,
                "original_stream": failure_record.original_stream,
                "error_type": type(e).__name__,
                "error_message": f"Original serialization failed: {e}",
                "failure_timestamp": failure_record.failure_timestamp.isoformat()
            })

        # Attempt to record failure in Redis and ACK the original message
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                # Store the JSON string in the DLQ hash
                pipe.hset(target_hash, failure_record.original_event_id, failure_json)
                # ACK the original message in the stream
                pipe.xack(
                    failure_record.original_stream,
                    failure_record.original_group,
                    failure_record.original_event_id
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
                exc_info=True 
            )
            return False

    # --- Live Tracking / Dashboard Features ---
    async def get_live_match_ids(self) -> Set[int]:
        """Gets current live match IDs from the set."""
        try:
            ids_raw = await self.redis.smembers(MATCH_SET) # type: ignore
            if not ids_raw:
                return set()
            
            return {int(id_str) for id_str in ids_raw}
        except Exception as e:
            logger.error(f"Failed getting live match IDs: {e}", exc_info=True)
            return set()