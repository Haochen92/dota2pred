import redis
from typing import Dict, Any, Set, Optional, List
from redis_client import RedisClient
from src.utils.set_logging import get_logger
from src.postgresql import get_async_engine
from pydantic_models.match import Match
from .redis_constants import ONGOING_STREAM, PREDICTED_STREAM, PREDICTION_GROUP, COMPLETION_GROUP
from .fetch_live_match import get_current_matches
from live_pipeline import (NewMatchProcessor,  
    OngoingMatchProcessor, PredictedMatchProcessor, LiveMatchStorage, LiveMatchTracker)

logger = get_logger(__name__)

class MatchPipelineOrchestrator:
    """Pipeline for processing live matches, making predictions, and tracking outcomes."""
    
    def __init__(self, env:str = 'prod'):
        self.env = env
        self.redis = RedisClient.get_instance(self.env)
        self.engine = get_async_engine(self.env)
        self._ensure_consumer_groups()
        self._initialize_storage()
        
    def _ensure_consumer_groups(self) -> None:
        self._create_group(ONGOING_STREAM, PREDICTION_GROUP)
        self._create_group(PREDICTED_STREAM, COMPLETION_GROUP)
    
    def _initialize_storage(self) -> None:
        self.storage = LiveMatchStorage(self.engine)
        
    def _create_group(self, stream:str, group:str) -> None:
        try:
            self.redis.xgroup_create(stream, group, id='0', mkstream=True)
            logger.info(f"Created consumer group {group} for stream {stream}")
        except redis.exceptions.ResponseError as e:
            if 'BUSYGROUP' in str(e):
                logger.info(f"Consumer group {group} already exists")
            else:
                logger.error(f"Error creating group {group}: {str(e)}")
                raise 
    
    async def run_cycle(self) -> Optional[List[Match]]:
        # Statistics of total matches performed
        try:
            # get current live matches
            curr_match_details = await get_current_matches()
            curr_match_ids = list(curr_match_details.keys())
            
            # Identify new matches and update tracking
            live_tracker = LiveMatchTracker(self.redis)
            new_match_ids_set = live_tracker.identify_new_matches(curr_match_ids)
            
            # process new matches
            new_match_processor = NewMatchProcessor(self.redis, self.storage)
            count_new_matches = new_match_processor.process_new_matches(new_match_ids_set, curr_match_details)
                        
            # process ongoing matches
            ongoing_match_processor = OngoingMatchProcessor(self.redis, self.storage)
            count_ongoing_matches = ongoing_match_processor.process_ongoing_matches(curr_match_details)
            
            # process predicted matches
            prediced_match_processor = PredictedMatchProcessor(self.redis, self.storage)
            count_completed_matches = await self._process_ongoing_matches(curr_match_details)
            
            
            logger.info(
                f"""Pipeline stats: 
                new_matches: {count_new_matches}
                predicted_matches {count_predicted_matches} 
                completed_matches: {count_completed_matches}
                """
            )
                       
            return curr_match_details
        
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error: {str(e)}")
            return None
        except Exception as e:
            import traceback
            logger.error(f"Unexpected error in poll_live_matches: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
        
    