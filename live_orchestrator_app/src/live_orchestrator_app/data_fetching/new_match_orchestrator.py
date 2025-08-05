from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.async_utils import TaskRunner
from .new_match_data_provider import NewMatchDataProvider
from .new_match_event_processor import NewMatchEventProcessor
from dota_oracle_common.models.utils import AsyncTask
from ..services.redis_service import RedisService

logger = get_logger(__name__)


class NewMatchOrchestrator:
    """Orchestrator for new match discovery and processing pipeline."""

    def __init__(
        self,
        data_provider: NewMatchDataProvider,
        event_processor: NewMatchEventProcessor,
        redis_service: RedisService,
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
        new_matches = await self.data_provider.get_new_ongoing_matches()
        if not new_matches:
            logger.debug("No new matches to process")
            return 0

        logger.info(f"Processing {len(new_matches)} new matches")

        # 3. Create concurrent tasks
        concurrent_tasks = [
            AsyncTask(key=match.match_id, inputs=match, coro=self.event_processor.process_event(match))
            for match in new_matches
        ]

        # 4. Call event processor for each task via TaskRunner
        results = await TaskRunner.run_concurrently(concurrent_tasks)

        # 5. Process outcomes
        count_success = 0
        count_failure = 0

        for task_result in results:
            try:
                transformed_match = task_result.outcome
                if isinstance(transformed_match, BaseException):
                    raise transformed_match
                await self.redis.publish_new_match_to_feature_eng(transformed_match)
                count_success += 1
            except Exception:
                count_failure += 1
                logger.warning(f"A new match processing task failed for match_id: {task_result.key}")
                continue

        logger.info(f"New match cycle complete: successful={count_success}, failed={count_failure}")
        return count_success
