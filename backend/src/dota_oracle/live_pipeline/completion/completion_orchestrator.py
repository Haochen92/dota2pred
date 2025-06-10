from dota_oracle.models.redis.schema import StreamMatchEventData
from dota_oracle.utils.set_logging import get_logger
from ..services.redis_service import RedisService
from ..services.history_update_service import HistoryUpdateService
from dota_oracle.constants.redis_constants import STREAM_PENDING_COMPLETION, COMPLETION_GROUP
from .completion_data_provider import CompletionDataProvider
from dota_oracle.utils.async_utils import TaskRunner
from dota_oracle.models.utils import AsyncTask
from .completion_event_processor import CompletionEventProcessor

logger = get_logger(__name__)

class CompletionOrchestrator:
    def __init__(
        self,
        redis_service: RedisService,
        history_update_service: HistoryUpdateService,
        completion_data_provider: CompletionDataProvider,
        completion_event_processor: CompletionEventProcessor
    ):
        self.redis = redis_service
        self.history_updater = history_update_service
        self.data_provider = completion_data_provider
        self.processor = completion_event_processor
    
    async def run_completion_cycle(self) -> int:
        """Process predicted matches for completion.
        
        Args:
            curr_matches: Dictionary of match_id to match details
        """
        # Retrieve work items from redis and match api for matches in events that have completed
        
        completion_work_items = await self.data_provider.get_work_items('consumer_one')
        
        if not completion_work_items:
            return 0
        
        concurrent_tasks = []
        work_item_map = {}
        
        for item in completion_work_items:
            task = AsyncTask(
                key=item.event_id,
                coro=self.processor.process_events(item)
            )
            concurrent_tasks.append(task)
            # populate map for faster lookup
            work_item_map[item.event_id] = item.event_data
            
        results = await TaskRunner.run_concurrently(concurrent_tasks)
        
        count_success = 0
        count_failure = 0
        
        for task_result in results:
            event_id: str = task_result.key
            event_data: StreamMatchEventData = work_item_map[event_id]
            try:
                result = task_result.get_result()
                if isinstance(result, Exception):
                    raise result
                await self.redis.mark_match_as_completed(
                    match_id= event_data.match_id,
                    event_id_to_ack=event_id
                )
                count_success += 1
            except Exception as e:
                await self.redis.handle_processing_failure(
                        event_data=event_data,
                        event_id=event_id,
                        error=e,
                        consumer_group=COMPLETION_GROUP,
                        event_stream=STREAM_PENDING_COMPLETION
                    )
                count_failure += 1
                continue
            
        logger.info(f"Completion Orchestrator: Successfully processed {count_success} and failed {count_failure}")
        
        return count_success
