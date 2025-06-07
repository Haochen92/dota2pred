from typing import List, Dict
from dota_oracle.utils.set_logging import get_logger
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.models.match import MatchTable
from dota_oracle.models.redis.schema import StreamMatchEventData
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from ..services.redis_service import RedisService
from dota_oracle.models.pipeline import FeatureEngineeringWorkItem

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = 'consumer_one'

class FeatureEngineeringDataProvider:
    """Data provider for feature engineering pipeline."""
    
    def __init__(self, redis_service: RedisService, db_engine: AsyncEngine):
        self.redis = redis_service
        self.engine = db_engine
    
    async def get_work_items(self, consumer_name: str = DEFAULT_CONSUMER_NAME) -> List[FeatureEngineeringWorkItem]:
        """
        Fetches pending feature engineering events and corresponding match data.
        
        Args:
            consumer_name: Redis consumer name
            
        Returns:
            List of FeatureEngineeringWorkItem for processing
        """
        # Fetch pending events from Redis
        pending_events = await self.redis.fetch_new_matches_for_feature_eng(consumer_name)
        
        if not pending_events:
            logger.info("No events pending feature engineering")
            return []
        
        logger.info(f"Retrieved {len(pending_events)} pending events from Redis stream")
        
        # Validate events and extract match IDs
        valid_events = self._validate_events(pending_events)
        if not valid_events:
            logger.warning("No valid events found after validation")
            return []
        
        # Fetch match details from database
        match_data_lookup = await self._fetch_match_details(valid_events)
        
        # Create work items for events that have corresponding match data
        work_items = []
        for event_id, event_data in valid_events.items():
            match_id = event_data.match_id
            match_details = match_data_lookup.get(match_id)
            
            if match_details:
                work_item = FeatureEngineeringWorkItem(
                    event_id=event_id,
                    event_data=event_data,
                    match_details=match_details
                )
                work_items.append(work_item)
            else:
                logger.warning(f"No match data found for event {event_id}, match_id {match_id}")
        
        logger.info(f"Created {len(work_items)} work items for feature engineering")
        return work_items
    
    def _validate_events(self, events: Dict[str, StreamMatchEventData]) -> Dict[str, StreamMatchEventData]:
        """Validates event data and returns only valid events."""
        valid_events = {}
        
        for event_id, event_data in events.items():
            if self._is_event_data_valid(event_data):
                valid_events[event_id] = event_data
            else:
                logger.warning(f"Invalid event data for event_id='{event_id}': {event_data}")
        
        logger.info(f"Event validation: valid={len(valid_events)}, invalid={len(events) - len(valid_events)}")
        return valid_events
    
    def _is_event_data_valid(self, event_data: StreamMatchEventData) -> bool:
        """Validates individual event data."""
        if not event_data:
            return False
        
        if not hasattr(event_data, 'match_id') or not event_data.match_id:
            return False
        
        if not isinstance(event_data.match_id, int) or event_data.match_id <= 0:
            return False
        
        return True
    
    async def _fetch_match_details(self, events: Dict[str, StreamMatchEventData]) -> Dict[int, MatchTable]:
        """Fetches match details from database for all events."""
        match_ids = [event_data.match_id for event_data in events.values()]
        unique_match_ids = list(set(match_ids))  # Remove duplicates
        
        logger.info(f"Fetching match details for {len(unique_match_ids)} unique matches")
        
        try:
            async with AsyncSession(self.engine) as session:
                match_repository = MatchRepository(session=session)
                
                match_details_list = await match_repository.get_match_details(
                    input_id_list=unique_match_ids
                )
                
                if not match_details_list:
                    logger.warning("No match details found in database")
                    return {}
                
                # Create lookup dictionary
                match_data_lookup = {
                    match.match_id: match for match in match_details_list
                }
                
                found_count = len(match_data_lookup)
                missing_count = len(unique_match_ids) - found_count
                
                logger.info(f"Match data retrieval: found={found_count}, missing={missing_count}")
                
                if missing_count > 0:
                    missing_ids = set(unique_match_ids) - set(match_data_lookup.keys())
                    logger.warning(f"Missing match details for IDs: {missing_ids}")
                
                return match_data_lookup
                
        except Exception as e:
            logger.error(f"Database error while fetching match details: {e}", exc_info=True)
            return {}