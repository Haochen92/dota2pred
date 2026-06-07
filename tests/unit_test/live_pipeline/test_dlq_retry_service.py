import pytest
from unittest.mock import AsyncMock, MagicMock

from dota_oracle_common.constants.redis_constants import DLQ_RETRY_COUNTS_HASH
from live_orchestrator_app.services.dlq_retry_service import DlqRetryService


pytestmark = pytest.mark.asyncio


def _make_service(max_retries: int = 3) -> DlqRetryService:
    redis_service = MagicMock()
    redis_service.redis = AsyncMock()
    return DlqRetryService(redis_service=redis_service, max_retries=max_retries)


async def test_cleanup_runs_before_reinjection():
    """Regression: stale-count cleanup must run BEFORE the reinject loop.

    Running it after the loop wiped a just-reinjected match's count every sweep (the match is
    transiently absent from the DLQ until it re-fails in a later stage), so `max_retries` never
    tripped and permanently-failing matches churned forever.
    """
    service = _make_service()
    service.redis.hgetall = AsyncMock(return_value={"evt-1": "{}"})

    record = MagicMock()
    record.original_data.match_id = 555
    service._parse_failure_record = MagicMock(return_value=record)
    service._get_retry_count = AsyncMock(return_value=0)
    service._reinject_event = AsyncMock(return_value=True)
    service._drop_exhausted_event = AsyncMock()
    service._cleanup_stale_counts = AsyncMock()

    manager = MagicMock()
    manager.attach_mock(service._cleanup_stale_counts, "cleanup")
    manager.attach_mock(service._reinject_event, "reinject")

    await service._process_dlq_hash("stream", "dlq_hash")

    # Cleanup must come first, then the reinjection.
    assert [c[0] for c in manager.mock_calls] == ["cleanup", "reinject"]
    service._drop_exhausted_event.assert_not_awaited()


async def test_under_cap_event_is_reinjected():
    """A match below the retry cap is reinjected, not dropped."""
    service = _make_service(max_retries=3)
    service.redis.hgetall = AsyncMock(return_value={"evt-1": "{}"})

    record = MagicMock()
    record.original_data.match_id = 111
    service._parse_failure_record = MagicMock(return_value=record)
    service._get_retry_count = AsyncMock(return_value=2)  # below cap
    service._reinject_event = AsyncMock(return_value=True)
    service._drop_exhausted_event = AsyncMock()
    service._cleanup_stale_counts = AsyncMock()

    reinjected = await service._process_dlq_hash("stream", "dlq_hash")

    assert reinjected == 1
    service._reinject_event.assert_awaited_once()
    service._drop_exhausted_event.assert_not_awaited()


async def test_exhausted_event_is_dropped_not_reinjected():
    """Once retry_count reaches max_retries the event is permanently dropped, not reinjected."""
    service = _make_service(max_retries=3)
    service.redis.hgetall = AsyncMock(return_value={"evt-1": "{}"})

    record = MagicMock()
    record.original_data.match_id = 777
    service._parse_failure_record = MagicMock(return_value=record)
    service._get_retry_count = AsyncMock(return_value=3)  # exhausted
    service._reinject_event = AsyncMock(return_value=True)
    service._drop_exhausted_event = AsyncMock()
    service._cleanup_stale_counts = AsyncMock()

    reinjected = await service._process_dlq_hash("stream", "dlq_hash")

    assert reinjected == 0
    service._reinject_event.assert_not_awaited()
    service._drop_exhausted_event.assert_awaited_once()
    # retry_key is "<stream>:<match_id>"
    assert service._drop_exhausted_event.await_args.args[2] == "stream:777"


async def test_drop_exhausted_event_removes_from_dlq_and_counts():
    """Dropping clears both the DLQ entry and the match's retry-count, so nothing lingers."""
    service = _make_service()

    pipe = MagicMock()
    pipe.execute = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=pipe)
    cm.__aexit__ = AsyncMock(return_value=False)
    service.redis.pipeline = MagicMock(return_value=cm)

    record = MagicMock()
    record.original_event_id = "evt-9"

    await service._drop_exhausted_event(record, "dlq_hash", "stream:777")

    pipe.hdel.assert_any_call("dlq_hash", "evt-9")
    pipe.hdel.assert_any_call(DLQ_RETRY_COUNTS_HASH, "stream:777")
    pipe.execute.assert_awaited_once()
