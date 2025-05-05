import redis.asyncio as redis
import time
import asyncio 
from utils.set_logging import get_logger 
from typing import List, Dict, Set, Any
import json

# Constants
from constants.redis_constants import (
    MATCH_SET, MATCH_STATUS, TMP_KEY,
    STREAM_NEW_MATCHES, STREAM_PENDING_PREDICTION, STREAM_PENDING_COMPLETION,
    FEATURE_ENGINEER_GROUP, PREDICTION_GROUP, COMPLETION_GROUP,
    FAILED_EVENTS_MAPPING
)

logger = get_logger(__name__)

class RedisService:
    def __init__(self, redis_client: redis.Redis):
        # Expects an asyncio Redis client, ideally configured with decode_responses=True
        self.redis: redis.Redis = redis_client
        self._initialized = False

    # --- Initialization ---
    async def initialize(self):
        """Asynchronous initializer. Ensures consumer groups exist."""
        if self._initialized:
            return

        logger.info("Initializing RedisService: Ensuring consumer groups exist...")
        # Use gather for potential concurrency during setup
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
        except redis.exceptions.ResponseError as e:
            if 'BUSYGROUP Consumer Group name already exists' in str(e):
                logger.info(f"Consumer group '{group}' already exists for stream '{stream}'.")
            else:
                logger.error(f"Error creating/checking group '{group}' for stream '{stream}': {e}", exc_info=True)
                raise 

    # --- Helper functions ---
    async def _fetch_events( self, group: str, consumer: str, stream: str, batch: int) -> Dict[str, dict]:
        """Fetches batch of events, returns dict {event_id: data_dict}."""
        try:
            events = await self.redis.xreadgroup(group, consumer, {stream: '>'}, count=batch, block=1000 )
            if not events:
                return {}

            _stream_name_bytes, stream_events_data = events[0]

            decoded_events = {}
            for event_id_bytes, data_dict_str in stream_events_data:
                try:
                     event_id = event_id_bytes.decode('utf-8')
                     decoded_events[event_id] = data_dict_str
                except UnicodeDecodeError:
                     logger.warning(f"Could not decode event ID {event_id_bytes!r} for stream {stream}", exc_info=False)
                     continue
            return decoded_events
        except redis.exceptions.TimeoutError:
            return {} # Normal, no events
        except Exception as e:
            logger.error(f"Error reading stream {stream} for group {group}: {e}", exc_info=True)
            return {} # Return empty on error


    # --- NEW MATCHES STAGE ---
    async def update_live_match_set_and_get_new(self, curr_ids: List[int]) -> Set[int]:
        """Updates tracked set atomically using RENAME, returns new IDs."""
        new_match_ids: Set[int] = set()
        curr_ids_str = [str(id) for id in curr_ids] 
        try:
            await self.redis.delete(TMP_KEY)
            if curr_ids_str:
                await self.redis.sadd(TMP_KEY, *curr_ids_str)

            # Result is Set[str] if decode_responses=True
            new_ids_str = await self.redis.sdiff(TMP_KEY, MATCH_SET)
            new_match_ids = {int(id_str) for id_str in new_ids_str} # Set comprehension

            await self.redis.rename(TMP_KEY, MATCH_SET)
            logger.info(f"Updated live match set. Found {len(new_match_ids)} new matches.")
        except Exception as e:
            logger.error(f"Failed to update live match set: {e}", exc_info=True)
            await self.redis.delete(TMP_KEY) 
            return set()
        return new_match_ids

    async def add_match_for_processing(self, match_id: int) -> bool:
        """Atomically sets initial status and adds match to the first stream."""
        match_id_str = str(match_id)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.hset(f'{MATCH_STATUS}:{match_id_str}', 'status', 'new') # Initial status
                pipe.xadd(STREAM_NEW_MATCHES, {'match_id': match_id_str, 'timestamp': timestamp})
                await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Failed adding match {match_id} to stream {STREAM_NEW_MATCHES}: {e}", exc_info=True)
            return False

    # --- FEATURE ENGINEERING STAGE ---
    async def fetch_new_matches_for_feature_eng(self, consumer: str, count: int=10) -> Dict[str, dict]:
        """Fetches events from the new matches stream."""
        return await self._fetch_events(FEATURE_ENGINEER_GROUP, consumer, STREAM_NEW_MATCHES, count)

    async def advance_match_to_pending_prediction(self, match_id: int, event_id_to_ack: str) -> bool:
        """Atomically updates status, adds to next stream, ACKs previous stream event."""
        match_id_str = str(match_id)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.hset(f'{MATCH_STATUS}:{match_id_str}', 'status', 'pending_prediction')
                pipe.xadd(STREAM_PENDING_PREDICTION, {'match_id': match_id_str, 'timestamp': timestamp})
                pipe.xack(STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP, event_id_to_ack)
                await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Redis failure advancing match {match_id} to pending prediction (ACK ID: {event_id_to_ack}): {e}", exc_info=True)
            return False

    # --- PREDICTION STAGE ---
    async def fetch_matches_pending_prediction(self, consumer: str, count: int=10) -> Dict[str, dict]:
        """Fetches events from the pending prediction stream."""
        return await self._fetch_events(PREDICTION_GROUP, consumer, STREAM_PENDING_PREDICTION, count)

    async def advance_match_to_pending_completion(self, match_id: int, event_id_to_ack: str) -> bool:
        """Atomically updates status, adds to next stream, ACKs previous stream event."""
        match_id_str = str(match_id)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.hset(f'{MATCH_STATUS}:{match_id_str}', 'status', 'pending_completion')
                pipe.xadd(STREAM_PENDING_COMPLETION, {'match_id': match_id_str, 'timestamp': timestamp})
                pipe.xack(STREAM_PENDING_PREDICTION, PREDICTION_GROUP, event_id_to_ack)
                await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Redis failure advancing match {match_id} to pending completion (ACK ID: {event_id_to_ack}): {e}", exc_info=True)
            return False

    # --- PENDING COMPLETION STAGE ---
    async def fetch_matches_pending_completion(self, consumer: str, count: int=10) -> Dict[str, dict]:
        """Fetches events from the pending completion stream."""
        return await self._fetch_events(COMPLETION_GROUP, consumer, STREAM_PENDING_COMPLETION, count)

    async def mark_match_as_completed(self, match_id: int, event_id_to_ack: str) -> bool:
        """Atomically deletes status hash and ACKs the final processing stream event."""
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

    # --- FAILURE HANDLING (DLQ) ---
    async def record_failure_and_ack(
        self,
        original_stream: str,
        group: str,
        event_id: str,
        event_data: Dict[str, Any],
        error: Exception
    ) -> bool:
        """Records failure details to DLQ Hash and ACKs original message."""
        target_hash = FAILED_EVENTS_MAPPING.get(original_stream) # Use mapping correctly
        if not target_hash:
            logger.error(f"Unknown stream '{original_stream}' in FAILED_EVENTS_MAPPING. Cannot record failure or ACK event {event_id}.")
            return False # Cannot proceed

        failure_info = {
            "original_event_id": event_id,
            "original_stream": original_stream,
            "original_data": event_data, # May need careful serialization if complex
            "error_type": type(error).__name__,
            "error_message": str(error),
            "failure_timestamp": time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        }

        try:
            # Attempt JSON serialization
            failure_json = json.dumps(failure_info)
        except TypeError:
            logger.warning(f"Could not fully serialize failure data for event {event_id}, storing basic info.")
            # Simplify data before trying again
            failure_info["original_data"] = str(event_data) # Store as string representation
            failure_info["error_message"] = f"{failure_info['error_message']} (original data stringified)"
            try:
                 failure_json = json.dumps(failure_info)
            except TypeError:
                 # If even basic info fails, store minimal error
                 logger.error(f"Could not serialize basic failure info for event {event_id}.")
                 failure_json = json.dumps({"error": "Serialization failure", "event_id": event_id, "stream": original_stream})

        try:
            async with self.redis.pipeline(transaction=True) as pipe:
                pipe.hset(target_hash, event_id, failure_json)
                pipe.xack(original_stream, group, event_id)
                await pipe.execute()
            logger.warning(f"Recorded failure for event {event_id} from stream '{original_stream}' to hash '{target_hash}' and ACKed original.")
            return True
        except Exception as e:
            logger.critical(
                f"CRITICAL: Failed to record failure AND ACK original event {event_id} from stream '{original_stream}'. "
                f"Message may remain pending/cause blocking. Hash target: '{target_hash}'. Error: {e}",
                exc_info=True
            )
            return False

    # --- Live Tracking / Dashboard Features ---
    async def get_live_match_ids(self) -> Set[int]:
        """Gets current live match IDs from the set."""
        try:
            ids_str = await self.redis.smembers(MATCH_SET)
            return set(int(id_str) for id_str in ids_str)
        except Exception as e:
            logger.error(f"Failed getting live match IDs: {e}", exc_info=True)
            return set()

