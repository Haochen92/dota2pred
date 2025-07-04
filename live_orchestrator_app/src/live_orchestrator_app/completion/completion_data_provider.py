from dota_oracle_common.utils.set_logging import get_logger
from typing import List
from ..services.redis_service import RedisService
from ..services.fetch_outcome_service import FetchOutcomeService
from dota_oracle_common.models.pipeline import CompletionWorkItem
from dota_oracle_common.constants.redis_constants import STREAM_PENDING_COMPLETION

logger = get_logger(__name__)

class CompletionDataProvider:
    def __init__(
        self,
        redis_service: RedisService,
    ):
        self.redis = redis_service
     
    async def get_work_items(self, consumer_name: str = "default_consumer") -> List[CompletionWorkItem]:
        
        # Fetch all pending events
        events = await self.redis.fetch_matches_pending_completion(consumer_name)
        
        if not events: 
            logger.info(f"No events in {STREAM_PENDING_COMPLETION}")
            return []
        
        # For all matches in the pending list, attempt to retrieve their outcome by batch
        pending_id_list = [data.match_id for _, data in events.items()]
        logger.info(f"Found {len(pending_id_list)} events pending completion")
        outcome_map = await FetchOutcomeService.fetch_outcomes_batch(pending_id_list)
        
        if not outcome_map:
            logger.info("None of the currently predicted live matches have completed")
            return []
        
        work_item_list: List[CompletionWorkItem] = []
        # Filter and return completed matches
        for event_id, event_data in events.items():
            match_id = event_data.match_id
            outcome = outcome_map.get(match_id)
            
            if outcome:
                work_item = CompletionWorkItem(
                    event_id = event_id,
                    event_data = event_data,
                    outcome = outcome
                )
                
                work_item_list.append(work_item)
        
        return work_item_list