from data_extraction.fetch_match_details import fetch_match_details, MatchesAPIResponse
from pydantic_models.match import MatchesAPIResponse
from utils.set_logging import get_logger
from typing import Dict, Any, Set, Coroutine, List
from .history_update_service import HistoryUpdateService
from .redis_service import RedisService
from data_repository.match_repository import MatchRepository
from constants.redis_constants import STREAM_PENDING_COMPLETION, COMPLETION_GROUP
from utils.async_utils import get_outcome_concurrently, run_updates_as_group

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
    
    async def process_predicted_matches(self, curr_matches: Dict[int, Dict[str, Any]]) -> int:
        """Process predicted matches for completion.
        
        Args:
            curr_matches: Dictionary of match_id to match details
        """
        # Read new events from the predicted matches stream
        events = await self.redis.fetch_matches_pending_completion('consumer_one')
        
        if not events:
            return 0

        curr_match_set = set(curr_matches.keys())
        
        # Filter those match that were previously from event stream but is no longer live
        completed_matches = await self._filter_completed_matches(events=events, curr_match_set=curr_match_set)
        
        fetch_match_details_task_group: Dict[int, Coroutine[Any, Any, MatchesAPIResponse]] = {}
        
        for event_id , data in completed_matches.items():
            match_id = data.get('match_id')
            fetch_match_details_task_group[event_id] = fetch_match_details(match_id)
        
        # Fetch API responses
        outcome_dict: Dict[str, MatchesAPIResponse| Exception ] = await get_outcome_concurrently(
            fetch_match_details_task_group
        )
        
        events_processed = 0
        
        for event_id, match_model in outcome_dict.items():
            try:
                if match_model is None:
                    # Match result is not out yet, to wait for it in next event loop. 
                    logger.warning(f"Match {match_id} is completed but data not available from source")
                    continue
                
                if isinstance(match_model, Exception):
                    # Exception happened, to raise exception and log
                    raise match_model
                
                match_id = match_model.match_id
                match_outcome = match_model.radiant_win
                
                task_group: List[Coroutine[Any, Any, None]] = [
                    self.storage.insert_match_outcome(match_id, match_outcome),
                    self.history_updater.update_histories(match_model),
                    self.redis.mark_match_as_completed(match_id, event_id)
                ]
                
                await run_updates_as_group(task_group)
                events_processed += 1
            except Exception as e:
                original_data = completed_matches.get(event_id, None)
                logger.error(f"Failed to process predicted matches for event:{event_id}, data: {original_data} ")
                await self.redis.record_failure_and_ack(
                    original_stream=STREAM_PENDING_COMPLETION,
                    group=COMPLETION_GROUP,
                    event_id=event_id,
                    event_data=original_data,
                    error=e
                )
                continue
            

        return events_processed
    
    async def _filter_completed_matches(self, events: Dict[str, dict], curr_match_set: Set[int]) -> Dict[str, Dict[str, Any]]:
        
        completed_matches_dict = {}
        curr_match_set = await self.redis.get_live_match_ids()
        
        for event_id, data in events.items():
            raw_match_id = data.get('match_id')
            try:
                match_id = int(raw_match_id)
            except (TypeError, ValueError):
                logger.warning(f"Failed to find or convert match_id, value:{raw_match_id} in event: {event_id}")
                continue
            if match_id not in curr_match_set:
                completed_matches_dict[event_id] = data
            
        return completed_matches_dict
    
        