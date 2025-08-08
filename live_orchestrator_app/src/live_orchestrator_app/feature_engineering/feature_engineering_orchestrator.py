import pydantic
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.async_utils import TaskRunner
from dota_oracle_common.models.utils import AsyncTask
from dota_oracle_common.constants.redis_constants import STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP
from .feature_engineering_data_provider import FeatureEngineeringDataProvider
from .feature_engineering_processor import FeatureEngineeringEventProcessor
from ..redis_services.redis_service import RedisService

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = "consumer_one"


class FeatureEngineeringOrchestrator:
    """Orchestrator for feature engineering pipeline."""

    def __init__(
        self,
        redis_service: RedisService,
        data_provider: FeatureEngineeringDataProvider,
        event_processor: FeatureEngineeringEventProcessor,
        consumer_name: str = DEFAULT_CONSUMER_NAME,
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
        concurrent_tasks = [
            AsyncTask(key=item.event_id, inputs=item, coro=self.event_processor.process_event(item))
            for item in work_items
        ]

        # 4. Call event processor for each task via TaskRunner
        results = await TaskRunner.run_concurrently(concurrent_tasks)

        # 5. Process outcomes and handle failures
        count_success = 0
        count_failure = 0

        for task_result in results:
            event_id = task_result.key
            match_id = task_result.inputs.match_id
            try:
                prediction_payload = task_result.outcome
                if isinstance(prediction_payload, BaseException):
                    raise prediction_payload

                await self.redis.publish_features_to_prediction(
                    match_id=match_id, event_id_to_ack=event_id, features=prediction_payload
                )
                count_success += 1
                logger.debug(f"Successfully processed feature engineering for event {event_id}")

            except (pydantic.ValidationError, ValueError, KeyError, RuntimeError) as ve:
                count_failure += 1
                await self.redis.handle_processing_failure(
                    event_data=task_result.inputs,
                    event_id=event_id,
                    error=ve,
                    consumer_group=FEATURE_ENGINEER_GROUP,
                    event_stream=STREAM_NEW_MATCHES,
                )
            except Exception as e:
                logger.error(f"Unexcepted Error during cycle, {e}", exc_info=True)
                raise

        logger.info(
            f"Feature engineering cycle complete: "
            f"successful={count_success}, failed={count_failure}, total={len(work_items)}"
        )

        return count_success
