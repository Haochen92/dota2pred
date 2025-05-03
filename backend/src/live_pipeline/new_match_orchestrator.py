import redis
import time
from typing import Set, Dict, Any
from src.utils.set_logging import get_logger
from .redis_constants import MATCH_STATUS, ONGOING_STREAM
from utils.set_logging import get_logger
from .match_pipeline_orchestrator import MatchRepository

logger = get_logger(__name__)

class NewMatchProcessor:
    def __init__(self, redis_client: redis.Redis, storage: MatchRepository):
        self.redis = redis_client 
        self.storage = storage
        
    async def process_new_matches(self, new_match_ids: Set[int], curr_matches: Dict[int, Dict[str, Any]]) -> int:   
        
        if not new_match_ids:
            return 0
        logger.info("processing new matches...")
        
        matches_processed = 0
        pipe = self.redis.pipeline()
        
        for match_id in new_match_ids:
            # Store match to database
            try:
                match_data = curr_matches.get(match_id, {})
                if not match_data:
                    raise ValueError(f"{match_id} not found in current_matches")
                await self.storage.insert_match_details(match_data)
                await self._update_redis_stream(pipe, match_id)
                matches_processed += 1
            except Exception as e:
                logger.error(f"Failed to process new match {match_id}: {e}", exc_info=True)
                raise e
            
        pipe.execute()
        
        logger.info(f"processed {matches_processed} new matches")
        return matches_processed
    
    async def _update_redis_stream(self, pipe: redis.pipeline, match_id):
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        # update current match_status
        pipe.hset(f'{MATCH_STATUS}:{match_id}', 'status','ongoing')
        pipe.xadd(
            ONGOING_STREAM, 
            {'match_id': match_id, 'timestamp': timestamp}
        )
