"""Unit tests for transient-error retry on RedisService transactional publishes."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import redis.asyncio as redis

from live_orchestrator_app.redis_services.redis_service import RedisService

pytestmark = pytest.mark.asyncio


def _service_with_execute(execute_side_effect):
    """Build a RedisService whose pipeline.execute() follows the given side effect."""
    pipe = MagicMock()
    pipe.execute = AsyncMock(side_effect=execute_side_effect)

    pipeline_cm = MagicMock()
    pipeline_cm.__aenter__ = AsyncMock(return_value=pipe)
    pipeline_cm.__aexit__ = AsyncMock(return_value=False)

    client = MagicMock()
    client.pipeline = MagicMock(return_value=pipeline_cm)
    return RedisService(client), pipe


async def test_retries_transient_error_then_succeeds():
    svc, pipe = _service_with_execute([redis.ConnectionError("redis down"), None])
    builds: list[object] = []

    async def build(pipe_arg):
        builds.append(pipe_arg)

    await svc._run_transaction_with_retry(build)

    assert pipe.execute.await_count == 2
    # The whole transaction is rebuilt on each attempt, not just re-executed.
    assert len(builds) == 2


async def test_gives_up_after_max_attempts_and_reraises():
    svc, pipe = _service_with_execute(redis.ConnectionError("redis down"))

    async def build(pipe_arg):
        return None

    with pytest.raises(redis.ConnectionError):
        await svc._run_transaction_with_retry(build)

    assert pipe.execute.await_count == 3  # stop_after_attempt(3)


async def test_non_transient_error_is_not_retried():
    svc, pipe = _service_with_execute(ValueError("bad payload"))

    async def build(pipe_arg):
        return None

    with pytest.raises(ValueError):
        await svc._run_transaction_with_retry(build)

    assert pipe.execute.await_count == 1  # not a connection error -> no retry
