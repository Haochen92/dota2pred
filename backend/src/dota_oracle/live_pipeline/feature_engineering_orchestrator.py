import pandas as pd
from typing import Dict, Coroutine, Any
from utils.set_logging import get_logger
from .feature_engineering_service import FeatureEngineeringService
from .redis_service import RedisService
from constants.redis_constants import STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP
from data_repository.match_repository import MatchRepository
from utils.async_utils import run_updates_as_group, get_outcome_concurrently
from utils.time_utils import get_current_utc_iso_timestamp
from pydantic_models.redis_models import StreamMatchEventData, FailureRecord

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
        
        match_details_dict: Dict[int, Dict[str, Any]] = await self._fetch_matches_from_db(events)
        
        if not match_details_dict:
            logger.warning(f"no match details found in the database")
            return 0
        
        events_task_dict : Dict[str, Coroutine[Any, Any, Any]] = {}
        for event_id, data in events.items():
            match_id = data.match_id
            match_details = match_details_dict.get(match_id)
            input_dataframe = pd.DataFrame([match_details])
            
            events_task_dict[event_id] = self._engineer_and_update_redis(
                input_dataframe, 
                match_id,
                event_id,
                data
            )
        
        output_dict = await get_outcome_concurrently(events_task_dict)
        
        successful_events = 0
        failed_events = 0
        
        for event, outcome in output_dict.items():
            if outcome and not isinstance(outcome, Exception):
                successful_events += 1
            else:
                failed_events += 1
        
        logger.info(f"Feature engineering orchestrator orchestrated {successful_events} successful events, and {failed_events} failed events")
        return successful_events
    
    async def _engineer_and_update_redis(self, input_dataframe: pd.DataFrame, match_id: int, event_id: str, data: StreamMatchEventData) -> bool:
        task_group = [
            self.feature_engineering_service.create_and_store_features(input_dataframe),
            self.redis.advance_match_to_pending_prediction(match_id, event_id)
        ]
        try:
            await run_updates_as_group(task_group)
            return True
        except Exception as e:
            failure_record = FailureRecord(
                original_event_id=event_id,
                original_stream=STREAM_NEW_MATCHES,
                original_group=FEATURE_ENGINEER_GROUP,
                original_data=data,
                error_message=e,
                failure_timestamp=get_current_utc_iso_timestamp()
            )
            await self.redis.record_failure_and_ack(failure_record)
            return False
        
    
    
    async def _fetch_matches_from_db(self, events: Dict[str, StreamMatchEventData]) -> Dict[int, Dict[str, any]]:
        list_matches_instances = [data.match_id for _, data in events.items()]
        batch_matches = await self.storage.get_match_details_batch(list_matches_instances)
        
        if not batch_matches:
            return {}
        match_dict = {match.match_id : match.model_dump() for match in batch_matches}
        return match_dict
        