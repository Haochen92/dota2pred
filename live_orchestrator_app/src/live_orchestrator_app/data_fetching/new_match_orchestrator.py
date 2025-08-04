from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.async_utils import TaskRunner
from .new_match_data_provider import NewMatchDataProvider
from .new_match_event_processor import NewMatchEventProcessor

logger = get_logger(__name__)


class NewMatchOrchestrator:
    """Orchestrator for new match discovery and processing pipeline."""

    def __init__(self, data_provider: NewMatchDataProvider, event_processor: NewMatchEventProcessor):
        self.data_provider = data_provider
        self.event_processor = event_processor

        # Validation
        if not all([data_provider, event_processor]):
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

        # 4. Call event processor for each task via TaskRunner
        results = await TaskRunner.run_concurrently(concurrent_tasks)

        # 5. Process outcomes
        count_success = 0
        count_failure = 0

        for task_result in results:
            try:
                # get_result() raises the exception if the task failed
                task_result.get_result()
                count_success += 1
            except Exception:
                count_failure += 1
                logger.warning(f"A new match processing task failed for match_id: {task_result.key}")

        logger.info(f"New match cycle complete: successful={count_success}, failed={count_failure}")
        return count_success
