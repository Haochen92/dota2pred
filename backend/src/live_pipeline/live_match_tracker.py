import redis
from typing import List, Set, Dict, Any
from src.utils.set_logging import get_logger
from .redis_constants import MATCH_SET, MATCH_STATUS

'''
API service for frontend UI polling 
'''

logger = get_logger(__name__)

TMP_KEY = f'{MATCH_SET}:temp'

class LiveMatchTracker:
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    def _clear_tmp_key(self):
        self.redis.delete(TMP_KEY)
        
    def get_tracked_matches_with_status(self) -> Dict[int, Dict[str, Any]] :
        match_ids = self.redis.smembers(self.MATCH_SET)
        tracked_match_statuses = {}
        for id in match_ids:
            match_id_int = int(id)
            status_data = self.redis.hgetall(f'{MATCH_STATUS}:{id}')
            tracked_match_statuses[match_id_int] = status_data
        
        return tracked_match_statuses
            
    def identify_new_matches(self, curr_match_ids: List[int]) -> Set[int]:
        
        logger.info("indentifying new matches...")
        
        self._clear_tmp_key()
        if curr_match_ids:
            self.redis.sadd(TMP_KEY, *curr_match_ids)
            
            # find new matches
            new_matches_ids = self.redis.sdiff(TMP_KEY, MATCH_SET)
            self._update_live_match_set()
            
            logger.info(f"Found {len(new_match_sets)} new matches")
            new_match_sets = set(int(id) for id in new_matches_ids)
            return new_match_sets
        else:
            return set()
        
    def _update_live_match_set(self):
        # Replace main set with temp set
        if self.redis.exists(self.TMP_KEY):
            self.redis.rename(TMP_KEY, MATCH_SET)