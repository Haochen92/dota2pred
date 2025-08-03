import pydantic
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.async_utils import TaskRunner
from dota_oracle_common.models.utils import AsyncTask
from dota_oracle_common.constants.redis_constants import PREDICTION_GROUP, STREAM_PENDING_PREDICTION
from dota_oracle_common.models.redis.schema import StreamMatchEventData
from live_orchestrator_app.prediction.prediction_data_provider import PredictionDataProvider
from live_orchestrator_app.prediction.prediction_event_processor import PredictionEventProcessor
from live_orchestrator_app.services.redis_service import RedisService
from typing import Dict

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = "consumer_one"


class PredictionOrchestrator:
    """Orchestrator for prediction pipeline."""

    def __init__(
        self,
        redis_service: RedisService,
        data_provider: PredictionDataProvider,
        event_processor: PredictionEventProcessor,
        consumer_name: str = DEFAULT_CONSUMER_NAME,
    ):
        self.redis = redis_service
        self.data_provider = data_provider
        self.event_processor = event_processor
        self.consumer_name = consumer_name

        logger.info(
            f"Initialized PredictionOrchestrator for consumer '{self.consumer_name}' on stream '{STREAM_PENDING_PREDICTION}'"
        )

    async def run_prediction_cycle(self) -> int:
        """
        Executes a complete prediction cycle.

        Returns:
            Number of events successfully processed
        """
        logger.info(
            f"PredictionOrchestrator: Fetching from {STREAM_PENDING_PREDICTION} for consumer {self.consumer_name}"
        )

        # 1. Get work items from data provider
        work_items = await self.data_provider.get_work_items(self.consumer_name)
        if not work_items:
            logger.debug(f"PredictionOrchestrator: No new events in {STREAM_PENDING_PREDICTION}")
            return 0

        logger.info(f"PredictionOrchestrator: Processing {len(work_items)} work items")

        # 2. Create async concurrent task list
        concurrent_tasks = []
        work_item_map: Dict[str, StreamMatchEventData] = {}

        for work_item in work_items:
            task = AsyncTask(key=work_item.event_id, coro=self.event_processor.process_event(work_item))
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
                count_success += 1
                await self.redis.advance_match_to_pending_completion(match_id, event_id)
                logger.debug(f"Successfully processed prediction for event {event_id}")

            except (pydantic.ValidationError, ValueError, KeyError, RuntimeError) as ve:
                count_failure += 1
                await self.redis.handle_processing_failure(
                    event_data=event_data,
                    event_id=event_id,
                    error=ve,
                    consumer_group=PREDICTION_GROUP,
                    event_stream=STREAM_PENDING_PREDICTION,
                )
            except Exception as e:
                logger.error("Unexcepted Error during cycle, {e}", exc_info=e)
                raise
        logger.info(
            f"PredictionOrchestrator: Finished cycle, with {count_success} successful events, and {count_failure} failures"
        )

        return count_success
