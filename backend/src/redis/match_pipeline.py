import redis
import time
from typing import Dict, List, Any, Set, Optional
from src.utils.set_logging import get_logger
from src.fetch_data.fetch_live_leagues import retrieve_live_league_games

logger = get_logger(__name__)

# Constants
MATCH_SET = 'live_match_ids'
ONGOING_STREAM = 'ongoing_matches'
PREDICTED_STREAM = 'predicted_matches'
PREDICTION_GROUP = 'prediction_group'
COMPLETION_GROUP = 'completion_group'

class MatchPipeline:
    """Pipeline for processing live matches, making predictions, and tracking outcomes."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._ensure_consumer_groups()
        
    def _ensure_consumer_groups(self) -> None:
        self._create_group(ONGOING_STREAM, PREDICTION_GROUP)
        self._create_group(PREDICTED_STREAM, COMPLETION_GROUP)
        
    def _create_group(self, stream:str, group: str) -> None:
        try:
            self.redis.xgroup_create(stream, group, id='0', mkstream=True)
            logger.info(f"Created consumer group {group} for stream {stream}")
        except redis.exceptions.ResponseError as e:
            if 'BUSYGROUP' in str(e):
                logger.info(f"Consumer group {group} already exists")
            else:
                logger.error(f"Error creating group {group}: {str(e)}")
                raise 
    
    def poll_live_matches(self) -> int:
        
        try:
            # get current live matches
            curr_matches = self._get_current_matches()
            if not curr_matches:
                logger.info("No live matches found")
                return 0
            
            # update live matches set and identify new matches
            new_match_ids = self._update_live_matches_set(curr_matches)
            
            # process new matches
            self._process_new_matches(new_match_ids, curr_matches)
            
            # process ongoing matches
            self._process_ongoing_matches(curr_matches)
            
            # process predicted matches for completion
            self._process_predicted_matches(curr_matches)
            
            return len(new_match_ids)
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error in poll_live_matches: {str(e)}")
            return 0
        
    def _get_current_matches(self):
        