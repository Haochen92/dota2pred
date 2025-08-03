import pydantic
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.async_utils import TaskRunner
from dota_oracle_common.models.utils import AsyncTask
from .new_match_data_provider import NewMatchDataProvider
from .new_match_event_processor import NewMatchEventProcessor
from ..services.redis_service import RedisService

logger = get_logger(__name__)


class NewMatchOrchestrator:
    """Orchestrator for new match discovery and processing pipeline."""

    def __init__(
        self, data_provider: NewMatchDataProvider, event_processor: NewMatchEventProcessor, redis_service: RedisService
    ):
        self.data_provider = data_provider
        self.event_processor = event_processor
        self.redis = redis_service

        # Validation
        if not all([data_provider, event_processor, redis_service]):
            raise ValueError("All dependencies must be provided")

    async def run_new_match_cycle(self) -> int:
        """
        Executes one cycle of new match processing.

        Returns:
            Number of matches successfully processed
        """
        logger.info("Starting new match discovery cycle")

        # 1. Get work items from data provider
        work_items = await self.data_provider.get_work_items()
        if not work_items:
            logger.debug("No new matches to process")
            return 0

        logger.info(f"Processing {len(work_items)} new matches")

        # 2. Create async concurrent task list
        concurrent_tasks = []
        work_item_map = {}

        for work_item in work_items:
            task = AsyncTask(key=work_item.match_id, coro=self.event_processor.process_event(work_item))
            concurrent_tasks.append(task)
            # 3. Create map for failure handling
            work_item_map[work_item.match_id] = work_item

        # 4. Call event processor for each task via TaskRunner
        results = await TaskRunner.run_concurrently(concurrent_tasks)

        # 5. Process outcomes
        count_success = 0
        count_failure = 0

        for task_result in results:
            match_id = task_result.key
            work_item = work_item_map[match_id]

            try:
                result = task_result.get_result()
                if isinstance(result, Exception):
                    raise result
                count_success += 1
                await self.redis.add_match_for_processing(match_id)
                logger.debug(f"Successfully processed new match {match_id}")

            except (pydantic.ValidationError, ValueError, KeyError, RuntimeError) as ve:
                count_failure += 1
                logger.error(f"Failed to process new match {match_id}: {ve}", exc_info=True)
                # Note: No failure recording needed for new matches as they're not from Redis streams
            except Exception as e:
                logger.error("Unexcepted Error during cycle, {e}", exc_info=e)
                raise

        logger.info(f"New match cycle complete: successful={count_success}, failed={count_failure}")
        return count_success
