import pydantic
from sqlalchemy.exc import SQLAlchemyError

from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.async_utils import TaskRunner
from dota_oracle_common.models.utils import AsyncTask
from dota_oracle_common.constants.redis_constants import ODDS_GROUP, STREAM_PENDING_ODDS
from ..redis_services.redis_service import RedisService
from .odds_data_provider import OddsDataProvider
from .odds_event_processor import OddsEventProcessor

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = "consumer_one"


class OddsOrchestrator:
    """Terminal odds-capture stage. Runs in parallel with completion off the prediction fan-out.

    Mirrors the completion stage: pull resolved work items, persist each concurrently, then ACK +
    XDEL successes from the odds stream. Per-item failures are routed to the odds DLQ so one bad
    snapshot can't fail the stage; nothing downstream depends on this stage.
    """

    def __init__(
        self,
        redis_service: RedisService,
        data_provider: OddsDataProvider,
        event_processor: OddsEventProcessor,
        consumer_name: str = DEFAULT_CONSUMER_NAME,
    ):
        self.redis = redis_service
        self.data_provider = data_provider
        self.event_processor = event_processor
        self.consumer_name = consumer_name

    async def run_odds_cycle(self) -> int:
        """Executes one odds-capture cycle. Returns the number of snapshots stored."""
        work_items = await self.data_provider.get_work_items(self.consumer_name)
        if not work_items:
            logger.debug(f"OddsOrchestrator: No events in {STREAM_PENDING_ODDS}")
            return 0

        logger.info(f"OddsOrchestrator: Processing {len(work_items)} work items")

        concurrent_tasks = [
            AsyncTask(key=item.event_id, inputs=item, coro=self.event_processor.process_event(item))
            for item in work_items
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
                await self.redis.mark_odds_done(match_id=match_id, event_id_to_ack=event_id)
                count_success += 1

            except (pydantic.ValidationError, ValueError, KeyError, RuntimeError, SQLAlchemyError) as ve:
                # Per-match failures (e.g. a transient DB error) DLQ that one match, not the stage.
                await self.redis.handle_processing_failure(
                    event_data=original_event,
                    event_id=event_id,
                    error=ve,
                    consumer_group=ODDS_GROUP,
                    event_stream=STREAM_PENDING_ODDS,
                )
                count_failure += 1
                continue
            except Exception as e:
                logger.error(f"Unexpected error during odds cycle: {e}", exc_info=True)
                raise

        logger.info(f"OddsOrchestrator: Successfully stored {count_success} and failed {count_failure}")
        return count_success
