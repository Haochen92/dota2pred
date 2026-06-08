from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock
from sqlalchemy.exc import IntegrityError

from dota_oracle_common.constants.redis_constants import ODDS_GROUP, STREAM_PENDING_ODDS
from dota_oracle_common.models.redis.schema import ConsumedEvent
from dota_oracle_common.models.odds import OddsResultPayload, SnapshotKind, OddsSkipReason
from live_orchestrator_app.odds.odds_orchestrator import OddsOrchestrator

F_PATH = "live_orchestrator_app.odds.odds_orchestrator"


def _work_item(match_id: int = 12345, event_id: str = "event_123", skip: bool = False) -> ConsumedEvent:
    payload = OddsResultPayload(
        match_id=match_id,
        snapshot_kind=SnapshotKind.ENTRY,
        captured_at=datetime.now(timezone.utc),
        skip_reason=OddsSkipReason.NO_MARKET_FOUND if skip else None,
    )
    return ConsumedEvent[OddsResultPayload](match_id=match_id, event_id=event_id, payload=payload)


@pytest.fixture
def odds_orchestrator(mock_redis_service) -> OddsOrchestrator:
    return OddsOrchestrator(
        redis_service=mock_redis_service,
        data_provider=AsyncMock(),
        event_processor=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_run_odds_cycle_successfully(odds_orchestrator, mocker, task_result_factory) -> None:
    work_item = _work_item()
    task_result = task_result_factory.build(key=work_item.event_id, inputs=work_item, outcome=True)

    mock_get_work_items = mocker.patch.object(
        odds_orchestrator.data_provider, "get_work_items", return_value=[work_item]
    )
    mock_task_runner = mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently", return_value=[task_result])
    mock_mark_done = mocker.patch.object(odds_orchestrator.redis, "mark_odds_done")

    result = await odds_orchestrator.run_odds_cycle()

    assert result == 1
    mock_get_work_items.assert_awaited_once_with("consumer_one")
    mock_task_runner.assert_awaited_once()
    mock_mark_done.assert_awaited_once_with(match_id=work_item.match_id, event_id_to_ack=work_item.event_id)


@pytest.mark.asyncio
async def test_run_odds_cycle_no_work_items(odds_orchestrator, mocker) -> None:
    mocker.patch.object(odds_orchestrator.data_provider, "get_work_items", return_value=[])
    mock_task_runner = mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently")
    mock_mark_done = mocker.patch.object(odds_orchestrator.redis, "mark_odds_done")

    result = await odds_orchestrator.run_odds_cycle()

    assert result == 0
    mock_task_runner.assert_not_called()
    mock_mark_done.assert_not_called()


@pytest.mark.asyncio
async def test_run_odds_cycle_skip_is_stored_like_a_success(odds_orchestrator, mocker, task_result_factory) -> None:
    """A no-market skip is still a stored row -> it must be ACKed, not DLQ'd."""
    work_item = _work_item(skip=True)
    task_result = task_result_factory.build(key=work_item.event_id, inputs=work_item, outcome=True)

    mocker.patch.object(odds_orchestrator.data_provider, "get_work_items", return_value=[work_item])
    mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently", return_value=[task_result])
    mock_mark_done = mocker.patch.object(odds_orchestrator.redis, "mark_odds_done")
    mock_handle_failure = mocker.patch.object(odds_orchestrator.redis, "handle_processing_failure")

    result = await odds_orchestrator.run_odds_cycle()

    assert result == 1
    mock_mark_done.assert_awaited_once()
    mock_handle_failure.assert_not_called()


@pytest.mark.asyncio
async def test_run_odds_cycle_failure_is_dlqd(odds_orchestrator, mocker, task_result_factory) -> None:
    work_item = _work_item()
    error = IntegrityError("INSERT INTO match_odds_snapshots ...", {}, Exception("db down"))
    task_result = task_result_factory.build(key=work_item.event_id, inputs=work_item, outcome=error)

    mocker.patch.object(odds_orchestrator.data_provider, "get_work_items", return_value=[work_item])
    mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently", return_value=[task_result])
    mock_mark_done = mocker.patch.object(odds_orchestrator.redis, "mark_odds_done")
    mock_handle_failure = mocker.patch.object(odds_orchestrator.redis, "handle_processing_failure")

    result = await odds_orchestrator.run_odds_cycle()

    assert result == 0
    mock_mark_done.assert_not_called()
    mock_handle_failure.assert_awaited_once_with(
        consumer_group=ODDS_GROUP,
        event_stream=STREAM_PENDING_ODDS,
        error=error,
        event_data=work_item,
        event_id=work_item.event_id,
    )
