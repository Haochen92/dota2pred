from dota_oracle.data_extraction.fetch_match_details import fetch_match_details, MatchesAPIResponse
from dota_oracle.pydantic_models.match import MatchesAPIResponse
from dota_oracle.pydantic_models.redis_models import StreamMatchEventData, FailureRecord
from dota_oracle.utils.set_logging import get_logger
from typing import Dict, Any, Set, Coroutine, List
from .history_update_service import HistoryUpdateService
from .redis_service import RedisService
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.constants.redis_constants import STREAM_PENDING_COMPLETION, COMPLETION_GROUP
from dota_oracle.utils.time_utils import get_current_utc_iso_timestamp
from dota_oracle.utils.async_utils import get_outcome_concurrently, run_updates_as_group

logger = get_logger(__name__)

class CompletionOrchestrator:
    def __init__(
        self, 
        redis_service: RedisService,
        history_update_service: HistoryUpdateService,
        match_repository: MatchRepository
    ):
        self.redis = redis_service
        self.history_updater = history_update_service
        self.storage = match_repository
    
    async def run_completion_cycle(self) -> int:
        """Process predicted matches for completion.
        
        Args:
            curr_matches: Dictionary of match_id to match details
        """
        # Read new events from the predicted matches stream
        
        events: Dict[str, StreamMatchEventData] = await self.redis.fetch_matches_pending_completion('consumer_one')
        
        if not events:
            return 0
        
        # Filter those match that were previously from event stream but is no longer live
        completed_matches: Dict[str, StreamMatchEventData] = await self._filter_completed_matches(events=events)
        
        fetch_match_details_task_group: Dict[str, Coroutine[Any, Any, MatchesAPIResponse | None]] = {}
        
        for event_id , data in completed_matches.items():
            fetch_match_details_task_group[event_id] = fetch_match_details(data.match_id)
        
        # Fetch API responses
        outcome_dict: Dict[str, MatchesAPIResponse| Exception | None ] = await get_outcome_concurrently(
            fetch_match_details_task_group
        )
        
        events_processed = 0
        for event_id, match_model in outcome_dict.items():
            original_data = completed_matches[event_id]
            match_id = original_data.match_id
            
            try:
                if match_model is None:

                    # Match result is not out yet, to wait for it in next event loop. 
                    logger.warning(f"Match {match_id} is completed but data not available from source")
                    continue
                
                if isinstance(match_model, Exception):
                    # Exception happened, to raise exception and log
                    logger.error(f"Exception when fetching match_details for {match_id}, e: {match_model}")
                    raise match_model
                
                match_id = match_model.match_id
                match_outcome = match_model.radiant_win
                
                task_group: List[Coroutine[Any, Any, None | bool]] = [
                    self.storage.insert_match_outcome(match_id, match_outcome),
                    self.history_updater.update_histories(match_model),
                    self.redis.mark_match_as_completed(match_id, event_id)
                ]
                
                await run_updates_as_group(task_group)
                events_processed += 1
            except Exception as e:
                data_dict = original_data.model_dump()
                logger.error(f"Failed to process predicted matches for event:{event_id}, data: {data_dict}")
                
                failure_record = FailureRecord(
                    original_data=original_data,
                    original_group=COMPLETION_GROUP,
                    original_event_id=event_id,
                    original_stream=STREAM_PENDING_COMPLETION,
                    error_type=str(type(e)),
                    error_message=str(e),
                    failure_timestamp=get_current_utc_iso_timestamp()
                )
                await self.redis.record_failure_and_ack(failure_record)
                continue
            

        return events_processed
    
    async def _filter_completed_matches(self, events: Dict[str, StreamMatchEventData]) -> Dict[str, StreamMatchEventData]:
        
        completed_matches_dict = {}
        curr_match_set: Set[int] = await self.redis.get_live_match_ids()
        
        for event_id, data in events.items():
            match_id = data.match_id
            if match_id not in curr_match_set:
                completed_matches_dict[event_id] = data
            
        return completed_matches_dict
    
        