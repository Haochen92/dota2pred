import pandas as pd
from typing import Dict, Coroutine, Any, List
from dota_oracle.utils.set_logging import get_logger
from .feature_engineering_service import FeatureEngineeringService
from .redis_service import RedisService
from dota_oracle.constants.redis_constants import STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.data_repository.schemas import MatchTable
from dota_oracle.utils.async_utils import run_updates_as_group, get_outcome_concurrently
from dota_oracle.utils.time_utils import get_current_utc_iso_timestamp
from dota_oracle.models.redis.schema import StreamMatchEventData, FailureRecord

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = 'consumer_one'

class FeatureEngineeringOrchestrator:
    """
    Orchestrates the feature engineering step by processing events from
    the new matches stream (STREAM_NEW_MATCHES).
    """
    def __init__(
        self,
        redis_service: RedisService,
        feature_engineering_service: FeatureEngineeringService,
        match_repository: MatchRepository,
        consumer_name: str = DEFAULT_CONSUMER_NAME
    ):
        self.redis = redis_service
        self.feature_engineering_service = feature_engineering_service
        self.consumer_name = consumer_name
        self.storage = match_repository
        logger.info(f"Initialized FeatureEngineeringOrchestrator for consumer '{self.consumer_name}' on stream '{STREAM_NEW_MATCHES}'")

    async def run_feature_engineering_cycle(self) -> int:
        """
        Fetches batch and process new matches for feature engineering 
        
        Returns:
            The number of events successfully processed in this cycle.
        """
        logger.info(f"FeatureEngineeringOrchestrator: Fetching from {STREAM_NEW_MATCHES} for consumer {self.consumer_name}...")

        events: Dict[str, StreamMatchEventData] = await self.redis.fetch_new_matches_for_feature_eng(self.consumer_name)

        if not events:
            logger.debug(f"FeatureEngineeringOrchestrator: No new events in {STREAM_NEW_MATCHES}")
            return 0
        else:
            logger.info(f"FeatureEngineeringOrchestrator: Found {len(events)} new events from {STREAM_NEW_MATCHES}")
        
        match_details_dict: Dict[int, MatchTable] = await self._fetch_matches_from_db(events)
        
        if not match_details_dict:
            logger.warning(f"no match details found in the database")
            return 0
        
        output_dict = await self._run_concurrent_tasks(match_details_dict, events)
        
        successful_events = sum(1 for val in output_dict.values() if val)
        failed_events = sum(1 for val in output_dict.values() if not val)
        
        logger.info(f"Feature engineering orchestrator orchestrated {successful_events} successful events, and {failed_events} failed events")
        return successful_events
    
    async def _engineer_and_update_redis(self, match_details: MatchTable, match_id: int, event_id: str, data: StreamMatchEventData) -> bool:
        task_group = [
            self.feature_engineering_service.create_and_store_features(match_details),
            self.redis.advance_match_to_pending_prediction(match_id, event_id)
        ]
        try:
            await run_updates_as_group(task_group)
            return True
        except Exception as e:
            await self._handle_processing_failure(data, event_id, e)
            return False
        
    
    
    async def _fetch_matches_from_db(self, events: Dict[str, StreamMatchEventData]) -> Dict[int, MatchTable]:
        list_matches_instances = [data.match_id for _, data in events.items()]
        batch_matches = await self.storage.get_match_details_batch(list_matches_instances)
        
        if not batch_matches:
            return {}
        
        matches_dict = {match_instance.match_id : match_instance for match_instance in batch_matches}
        return matches_dict
    
    async def _run_concurrent_tasks(
        self, 
        match_details: Dict[int, MatchTable], 
        events: Dict[str, StreamMatchEventData]
    )-> Dict[str, bool]:
        concurrent_task_dict : Dict[str, Coroutine[Any, Any, Any]] = {}
        for event_id, data in events.items():
            try:
                match_id = data.match_id
                match_details_instance = match_details.get(match_id)
                if not match_details_instance:
                    raise ValueError(f"match details for {match_id} is empty")
                
                concurrent_task_dict[event_id] = self._engineer_and_update_redis(
                    match_details_instance, 
                    match_id,
                    event_id,
                    data
                )
            except Exception as e:
                await self._handle_processing_failure(data, event_id, e)
                continue
        
        output_dict = await get_outcome_concurrently(concurrent_task_dict)
        return output_dict # type: ignore
        
    async def _handle_processing_failure(self, data: StreamMatchEventData, event_id: str, e: Exception) -> None:
        failure_record = FailureRecord(
                    original_event_id=event_id,
                    original_stream=STREAM_NEW_MATCHES,
                    original_group=FEATURE_ENGINEER_GROUP,
                    original_data=data,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    failure_timestamp=get_current_utc_iso_timestamp()
                )
        await self.redis.record_failure_and_ack(failure_record)
        