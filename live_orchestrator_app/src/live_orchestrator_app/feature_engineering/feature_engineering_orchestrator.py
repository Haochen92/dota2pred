from typing import Dict
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.async_utils import TaskRunner
from dota_oracle_common.models.utils import AsyncTask
from dota_oracle_common.constants.redis_constants import STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP
from dota_oracle_common.models.redis.schema import StreamMatchEventData
from .feature_engineering_data_provider import FeatureEngineeringDataProvider
from .feature_engineering_processor import FeatureEngineeringEventProcessor
from ..services.redis_service import RedisService

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = 'consumer_one'

class FeatureEngineeringOrchestrator:
    """Orchestrator for feature engineering pipeline."""
    
    def __init__(
        self,
        redis_service: RedisService,
        data_provider: FeatureEngineeringDataProvider,
        event_processor: FeatureEngineeringEventProcessor,
        consumer_name: str = DEFAULT_CONSUMER_NAME
    ):
        self.redis = redis_service
        self.data_provider = data_provider
        self.event_processor = event_processor
        self.consumer_name = consumer_name
        
        logger.info(
            f"Initialized FeatureEngineeringOrchestrator: "
            f"consumer='{self.consumer_name}', stream='{STREAM_NEW_MATCHES}'"
        )
    
    async def run_feature_engineering_cycle(self) -> int:
        """
        Executes a complete feature engineering cycle.
        
        Returns:
            Number of events successfully processed
        """
        logger.info(f"Starting feature engineering cycle for consumer '{self.consumer_name}'")
        
        # 1. Get work items from data provider
        work_items = await self.data_provider.get_work_items(self.consumer_name)
        if not work_items:
            logger.debug("No work items found - cycle complete")
            return 0
        
        logger.info(f"Processing {len(work_items)} work items")
        
        # 2. Create async concurrent task list
        concurrent_tasks = []
        work_item_map: Dict[str, StreamMatchEventData] = {}
        
        for work_item in work_items:
            task = AsyncTask(
                key=work_item.event_id,
                coro=self.event_processor.process_event(work_item)
            )
            concurrent_tasks.append(task)
            # 3. Create map for failure handling
            work_item_map[work_item.event_id] = work_item.event_data
        
        # 4. Call event processor for each task via TaskRunner
        results = await TaskRunner.run_concurrently(concurrent_tasks)
        
        # 5. Process outcomes and handle failures
        count_success = 0
        count_failure = 0
        
        for task_result in results:
            event_id = task_result.key
            event_data = work_item_map[event_id]
            match_id = event_data.match_id
            try:
                result = task_result.get_result()
                if isinstance(result, Exception):
                    raise result
                # Advance match to next stage in Redis
                await self.redis.advance_match_to_pending_prediction(match_id, event_id)
                count_success += 1
                logger.debug(f"Successfully processed feature engineering for event {event_id}")
                
            except Exception as e:
                count_failure += 1
                await self.redis.handle_processing_failure(
                    event_data=event_data,
                    event_id=event_id,
                    error=e,
                    consumer_group=FEATURE_ENGINEER_GROUP,
                    event_stream=STREAM_NEW_MATCHES
                )
        
        logger.info(
            f"Feature engineering cycle complete: "
            f"successful={count_success}, failed={count_failure}, total={len(work_items)}"
        )
        
        return count_success
    
