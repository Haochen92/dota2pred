from dota_oracle.models.redis.schema import StreamMatchEventData, FailureRecord
from dota_oracle.utils.set_logging import get_logger
from typing import Dict, Set, List, Tuple
from .history_update_service import HistoryUpdateService
from ..redis_service import RedisService
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.models.match import MatchOutcomeTable
from dota_oracle.constants.redis_constants import STREAM_PENDING_COMPLETION, COMPLETION_GROUP
from dota_oracle.utils.time_utils import get_current_utc_iso_timestamp
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from .fetch_outcome_service import FetchOutcomeService

logger = get_logger(__name__)

class CompletionOrchestrator:
    def __init__(
        self,
        db_engine: AsyncEngine, 
        redis_service: RedisService,
        history_update_service: HistoryUpdateService,
        match_repository: MatchRepository
    ):
        self.engine = db_engine
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
            logger.info("No events in {STREAM_PENDING_PREDICTION}")
            return 0
        
        # Filter those match that were previously from event stream but is no longer live
        completed_events_dict, completed_matches_list = await self._filter_completed_matches(events=events)
        if not completed_events_dict or not completed_matches_list:
            logger.info("None of the currently predicted live matches have completed")
            return 0
        
        completed_outcome_dict = await FetchOutcomeService.fetch_outcomes_batch(completed_matches_list)
        
        if not completed_outcome_dict:
            logger.info("Failed to fetch any match outcomes for this cycle")
            return 0
        
        return await self._process_events(completed_events_dict, completed_outcome_dict)
        
        
    
    async def _filter_completed_matches(self, events: Dict[str, StreamMatchEventData]) -> Tuple[Dict[str, StreamMatchEventData], List[int]]:
        
        completed_events_dict = {}
        completed_matches_list = []
        curr_match_set: Set[int] = await self.redis.get_live_match_ids()
        
        for event_id, stream_event_data in events.items():
            match_id = stream_event_data.match_id
            if match_id not in curr_match_set:
                completed_events_dict[event_id] = stream_event_data
                completed_matches_list.append(match_id)
                
        return completed_events_dict, completed_matches_list
            
    async def _process_events(
        self,
        completed_match_dict: Dict[str, StreamMatchEventData],
        completed_outcome_dict: Dict[int, bool],
    ):
        events_processed = 0
        for event_id, stream_data in completed_match_dict.items():
            match_id = stream_data.match_id
            try:
                match_outcome = completed_outcome_dict.get(match_id, None)
                if not match_outcome:
                    logger.warning(f"Match {match_id} is completed but data not available from source")
                    continue
            
                await self._update_match_outcome(match_id, match_outcome)
                
                await self.history_updater.update_histories(match_id)
                
                await self.redis.mark_match_as_completed(match_id, event_id)
                
                events_processed += 1
            except Exception as e:
                await self._handle_processing_failure(stream_data, event_id, e)
                continue
        
        return events_processed
            
    async def _update_match_outcome(self, match_id: int, match_outcome: bool):
        try:
            outcome_instance = MatchOutcomeTable(match_id=match_id, radiant_win=match_outcome)
            
            async with AsyncSession(self.engine) as session:
                async with session.begin():
                    match_repository = MatchRepository(session=session)
                    await match_repository.insert_match_outcome([outcome_instance])
        except Exception as e:
            raise e
    
    async def _handle_processing_failure(self, data: StreamMatchEventData, event_id: str, e: Exception) -> None:
        data_dict = data.model_dump()
        logger.error(f"Failed to process predicted matches for event:{event_id}, data: {data_dict}")
        failure_record = FailureRecord(
                    original_data=data,
                    original_group=COMPLETION_GROUP,
                    original_event_id=event_id,
                    original_stream=STREAM_PENDING_COMPLETION,
                    error_type=str(type(e)),
                    error_message=str(e),
                    failure_timestamp=get_current_utc_iso_timestamp()
                )
        await self.redis.record_failure_and_ack(failure_record)