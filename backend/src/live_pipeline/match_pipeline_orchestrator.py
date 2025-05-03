# import typing
from typing import Dict, Any, Set, Optional, List
from pydantic_models.match 

# import logging
from src.utils.set_logging import get_logger

# import db engine
from src.postgresql import get_async_engine

# import redis & redis constants
import redis
from redis_client import RedisClient
from .redis_constants import ONGOING_STREAM, PREDICTED_STREAM, PREDICTION_GROUP, COMPLETION_GROUP

# import main processors
from .new_match_processor import NewMatchProcessor
from .ongoing_match_processor import OngoingMatchProcessor
from .predicted_match_processor import PredictedMatchProcessor

# import other pipeline classes
from .live_match_tracker import LiveMatchTracker

# import repository
from data_repository.features_repository import FeaturesRepository
from data_repository.heroes_repository import HeroesRepository
from data_repository.histories_repository import HistoryRepository
from data_repository.match_repository import MatchRepository
from data_repository.prediction_repository import PredictionRepository

# data extraction
from data_extraction.fetch_live_leagues import fetch_live_league_games, LiveLeagueGame

logger = get_logger(__name__)

class MatchPipelineOrchestrator:
    """Pipeline for processing live matches, making predictions, and tracking outcomes."""
    
    def __init__(self, env:str = 'prod'):
        self.env = env
        self.redis = RedisClient.get_instance(self.env)
        self.engine = get_async_engine(self.env)
        self._ensure_consumer_groups()
        self._instantiate_storage()
        self._instantiate_pipeline_classes()
        
    def _ensure_consumer_groups(self) -> None:
        self._create_group(ONGOING_STREAM, PREDICTION_GROUP)
        self._create_group(PREDICTED_STREAM, COMPLETION_GROUP)
    
    def _instantiate_storage(self) -> None:
        self.match_repository = MatchRepository(self.engine)
        self.features_repository = FeaturesRepository(self.engine)
        self.heroes_repository = HeroesRepository(self.engine)
        self.history_repository = HistoryRepository(self.engine)
        self.prediction_repository = PredictionRepository(self.engine)
        
    def _instantiate_pipeline_classes(self) -> None:
        self.new_match_processor = NewMatchProcessor(self.redis, self.match_repository)
        self.ongoing_match_processor = OngoingMatchProcessor(
            self.redis, 
            self.features_repository, 
            self.prediction_repository,
            self.heroes_repository,
            self.history_repository
        )
        self.predicted_match_processor = PredictedMatchProcessor(
            self.redis,
            self.history_repository,
            self.match_repository
        )
        self.live_match_tracker = LiveMatchTracker(self.redis)
        
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
    
    async def run_cycle(self) -> None:
        # Statistics of total matches performed
        try:
            # get current live matches
            curr_games: List[LiveLeagueGame] = await fetch_live_league_games()
            curr_match_dict = {item.match_id : item.model_dump() for item in curr_games}
            curr_match_ids = [key for key in curr_match_dict.keys()]
            
            # Identify new matches and update tracking
            new_match_ids_set = self.live_match_tracker.identify_new_matches(curr_match_ids)
            
            # process new matches
            count_new_matches = await \
                self.new_match_processor.process_new_matches(new_match_ids_set, curr_match_dict)
                        
            # process ongoing matches
            count_predicted_matches = await self.ongoing_match_processor.process_ongoing_matches(curr_match_dict)
            
            # process predicted matches
            count_completed_matches = await self.predicted_match_processor.(curr_match_dict)
            
            
            logger.info(
                f"""Pipeline stats: 
                new_matches: {count_new_matches}
                predicted_matches {count_predicted_matches} 
                completed_matches: {count_completed_matches}
                """
            )
                       
            return None
        
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error: {str(e)}")
            return None
        except Exception as e:
            import traceback
            logger.error(f"Unexpected error in poll_live_matches: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
        
    