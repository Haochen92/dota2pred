import pytest
from unittest.mock import AsyncMock, MagicMock

from dota_oracle_common.constants.redis_constants import DLQ_RETRY_COUNT_PREFIX
from live_orchestrator_app.services.dlq_retry_service import DlqRetryService


pytestmark = pytest.mark.asyncio


def _make_service(max_retries: int = 3) -> DlqRetryService:
    redis_service = MagicMock()
    redis_service.redis = AsyncMock()
    return DlqRetryService(redis_service=redis_service, max_retries=max_retries)


def _pipe_context(service) -> MagicMock:
    """Wire service.redis.pipeline() to return a mock transaction pipeline; return the pipe."""
    pipe = MagicMock()
    pipe.execute = AsyncMock()
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=pipe)
    cm.__aexit__ = AsyncMock(return_value=False)
    service.redis.pipeline = MagicMock(return_value=cm)
    return pipe


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

    reinjected = await service._process_dlq_hash("stream", "dlq_hash")

    assert reinjected == 0
    service._reinject_event.assert_not_awaited()
    service._drop_exhausted_event.assert_awaited_once()
    # retry_key is "<stream>:<match_id>"
    assert service._drop_exhausted_event.await_args.args[2] == "stream:777"


async def test_get_retry_count_reads_prefixed_key():
    """The count is read from the per-match TTL'd key, not a shared hash."""
    service = _make_service()
    service.redis.get = AsyncMock(return_value="2")

    count = await service._get_retry_count("stream:777")

    assert count == 2
    service.redis.get.assert_awaited_once_with(f"{DLQ_RETRY_COUNT_PREFIX}:stream:777")


async def test_reinject_increments_and_expires_count():
    """Reinjecting bumps the count key and refreshes its TTL (self-cleaning, no sweep needed)."""
    service = _make_service()
    pipe = _pipe_context(service)
    service.redis.get = AsyncMock(return_value="1")
    service.redis_service._publish_event = AsyncMock()

    record = MagicMock()
    record.original_event_id = "evt-1"
    record.original_data.match_id = 777
    record.original_data.payload = MagicMock()
    record.original_stream = "stream"

    ok = await service._reinject_event(record, "dlq_hash", "stream:777")

    assert ok is True
    pipe.hdel.assert_any_call("dlq_hash", "evt-1")
    pipe.incr.assert_called_once_with(f"{DLQ_RETRY_COUNT_PREFIX}:stream:777")
    pipe.expire.assert_called_once()
    assert pipe.expire.call_args.args[0] == f"{DLQ_RETRY_COUNT_PREFIX}:stream:777"
    pipe.execute.assert_awaited_once()


async def test_drop_exhausted_event_removes_from_dlq_and_count():
    """Dropping clears both the DLQ entry and the match's TTL'd count key, so nothing lingers."""
    service = _make_service()
    pipe = _pipe_context(service)

    record = MagicMock()
    record.original_event_id = "evt-9"

    await service._drop_exhausted_event(record, "dlq_hash", "stream:777")

    pipe.hdel.assert_any_call("dlq_hash", "evt-9")
    pipe.delete.assert_any_call(f"{DLQ_RETRY_COUNT_PREFIX}:stream:777")
    pipe.execute.assert_awaited_once()
