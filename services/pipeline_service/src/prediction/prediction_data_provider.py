from typing import List, Dict
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.models.redis.schema import StreamMatchEventData
from dota_oracle_common.constants.redis_constants import STREAM_PENDING_PREDICTION
from ..services.redis_service import RedisService
from dota_oracle_common.models.pipeline import PredictionWorkItem

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = 'consumer_one'

class PredictionDataProvider:
    """Data provider for prediction pipeline."""
    
    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
    
    async def get_work_items(self, consumer_name: str = DEFAULT_CONSUMER_NAME) -> List[PredictionWorkItem]:
        """
        Fetches pending prediction events from Redis.
        
        Args:
            consumer_name: Redis consumer name
            
        Returns:
            List of PredictionWorkItem for processing
        """
        logger.debug(f"Fetching events from stream '{STREAM_PENDING_PREDICTION}'")
        
        # Fetch pending events from Redis
        events: Dict[str, StreamMatchEventData] = await self.redis.fetch_matches_pending_prediction(consumer_name)
        
        if not events:
            logger.debug(f"No new events in {STREAM_PENDING_PREDICTION}")
            return []
        
        logger.info(f"Found {len(events)} new events from {STREAM_PENDING_PREDICTION}")
        
        # Validate events and create work items
        work_items = []
        for event_id, event_data in events.items():
            if self._is_event_data_valid(event_data):
                work_item = PredictionWorkItem(
                    event_id=event_id,
                    event_data=event_data,
                    match_id=event_data.match_id
                )
                work_items.append(work_item)
            else:
                logger.warning(f"Invalid event data for event_id='{event_id}': {event_data}")
        
        logger.info(f"Created {len(work_items)} valid work items for prediction")
        return work_items
    
    def _is_event_data_valid(self, event_data: StreamMatchEventData) -> bool:
        """Validates individual event data."""
        if not event_data:
            return False
        
        if not hasattr(event_data, 'match_id') or not event_data.match_id:
            return False
        
        if not isinstance(event_data.match_id, int) or event_data.match_id <= 0:
            return False
        
        return True