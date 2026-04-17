import pydantic
from dota_oracle_common.utils.set_logging import get_logger
from live_orchestrator_app.redis_services.redis_service import RedisService
from dota_oracle_common.constants.redis_constants import STREAM_PENDING_COMPLETION, COMPLETION_GROUP
from live_orchestrator_app.completion.completion_data_provider import CompletionDataProvider
from dota_oracle_common.utils.async_utils import TaskRunner
from dota_oracle_common.models.utils import AsyncTask
from live_orchestrator_app.completion.completion_event_processor import CompletionEventProcessor

logger = get_logger(__name__)


class CompletionOrchestrator:
    def __init__(
        self,
        redis_service: RedisService,
        completion_data_provider: CompletionDataProvider,
        completion_event_processor: CompletionEventProcessor,
    ):
        self.redis = redis_service
        self.data_provider = completion_data_provider
        self.processor = completion_event_processor

    async def run_completion_cycle(self) -> int:
        """Process predicted matches for completion.

        Args:
            curr_matches: Dictionary of match_id to match details
        """
        # Retrieve work items from redis and match api for matches in events that have completed
        logger.info("Starting Completion Cycle...")

        completion_work_items = await self.data_provider.get_work_items("consumer_one")

        logger.info(f"Found {len(completion_work_items)} completed live matches")

        if not completion_work_items:
            logger.info("None of the existing live matches have completed. Ending cycle early")
            return 0

        concurrent_tasks = [
            AsyncTask(key=item.event_id, inputs=item, coro=self.processor.process_events(item))
            for item in completion_work_items
        ]

        results = await TaskRunner.run_concurrently(concurrent_tasks)

        count_success = 0
        count_failure = 0

        for task_result in results:
            event_id: str = task_result.key
            original_event = task_result.inputs
            match_id = original_event.match_id
            try:
                result = task_result.outcome
                if isinstance(result, BaseException):
                    raise result
                await self.redis.mark_match_as_completed(match_id=match_id, event_id_to_ack=event_id)
                count_success += 1

            except (pydantic.ValidationError, ValueError, KeyError, RuntimeError) as ve:
                await self.redis.handle_processing_failure(
                    event_data=original_event,
                    event_id=event_id,
                    error=ve,
                    consumer_group=COMPLETION_GROUP,
                    event_stream=STREAM_PENDING_COMPLETION,
                )
                count_failure += 1
                continue
            except Exception as e:
                logger.error(f"Unexpected error during completion cycle: {e}", exc_info=True)
                raise

        logger.info(f"Completion Orchestrator: Successfully processed {count_success} and failed {count_failure}")

        return count_success
