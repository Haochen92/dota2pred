import pytest
from unittest.mock import AsyncMock, MagicMock

from dota_oracle_common.models.utils.schema import TaskResult
from live_orchestrator_app.constants.redis_constants import STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP
from live_orchestrator_app.feature_engineering.feature_engineering_orchestrator import (
    FeatureEngineeringOrchestrator,
)

pytestmark = pytest.mark.asyncio

TR_PATH = "live_orchestrator_app.feature_engineering.feature_engineering_orchestrator.TaskRunner.run_concurrently"


def _work_item(match_id: int, event_id: str) -> MagicMock:
    item = MagicMock()
    item.match_id = match_id
    item.event_id = event_id
    return item


def _orchestrator():
    redis = AsyncMock()
    data_provider = AsyncMock()
    event_processor = AsyncMock()
    orch = FeatureEngineeringOrchestrator(
        redis_service=redis,
        data_provider=data_provider,
        event_processor=event_processor,
    )
    return orch, redis, data_provider


async def test_data_error_is_terminally_discarded(mocker):
    """A permanent data failure (e.g. incomplete match data -> ValueError) is terminally
    discarded, NOT routed to the retryable DLQ where it would churn every sweep."""
    orch, redis, data_provider = _orchestrator()
    item = _work_item(match_id=8417545047, event_id="evt-1")
    data_provider.get_work_items = AsyncMock(return_value=[item])

    result = TaskResult(key="evt-1", inputs=item, outcome=ValueError("Incomplete features"))
    mocker.patch(TR_PATH, AsyncMock(return_value=[result]))

    await orch.run_feature_engineering_cycle()

    redis.discard_unresolvable_event.assert_awaited_once()
    kwargs = redis.discard_unresolvable_event.await_args.kwargs
    assert kwargs["match_id"] == 8417545047
    assert kwargs["event_id"] == "evt-1"
    assert kwargs["event_stream"] == STREAM_NEW_MATCHES
    assert kwargs["consumer_group"] == FEATURE_ENGINEER_GROUP
    redis.handle_processing_failure.assert_not_awaited()


async def test_runtime_error_goes_to_retryable_dlq(mocker):
    """A possibly-transient RuntimeError still routes to the retryable DLQ, not terminal discard."""
    orch, redis, data_provider = _orchestrator()
    item = _work_item(match_id=999, event_id="evt-2")
    data_provider.get_work_items = AsyncMock(return_value=[item])

    result = TaskResult(key="evt-2", inputs=item, outcome=RuntimeError("transient"))
    mocker.patch(TR_PATH, AsyncMock(return_value=[result]))

    await orch.run_feature_engineering_cycle()

    redis.handle_processing_failure.assert_awaited_once()
    redis.discard_unresolvable_event.assert_not_awaited()
