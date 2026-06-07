import pytest
from datetime import datetime, timedelta, timezone

from dota_oracle_common.models.redis.schema import CompletedMatchPayload, ConsumedEvent, CompletionPayload

from live_orchestrator_app.completion.completion_data_provider import CompletionDataProvider

F_PATH = "live_orchestrator_app.completion.completion_data_provider"


def _event_id(dt: datetime) -> str:
    """Build a Redis stream id (<ms>-<seq>) whose timestamp is `dt`."""
    return f"{int(dt.timestamp() * 1000)}-0"


def _recent_id() -> str:
    """An event id young enough to pass the free-feed freshness cutoff."""
    return _event_id(datetime.now(timezone.utc))


def _aged_id() -> str:
    """An event id older than the free-feed window (handed to the paid stale path)."""
    return _event_id(datetime.now(timezone.utc) - timedelta(hours=3))


@pytest.mark.asyncio
async def test_get_work_items_successfully(mock_redis_service, mock_stale_match_service, mocker) -> None:
    # ARRANGE
    match_id = 12345
    event_id = _recent_id()
    mock_outcome = True

    # Create ConsumedEvent with CompletionPayload - input from redis
    consumed_event = ConsumedEvent[CompletionPayload](
        match_id=match_id, event_id=event_id, payload=CompletionPayload(match_id=match_id, radiant_win=True)
    )

    mock_fetch_matches = mocker.patch.object(
        mock_redis_service, "fetch_matches_for_completion", return_value=[consumed_event]
    )

    mock_fetch_outcome = mocker.patch(
        f"{F_PATH}.FetchOutcomeService.fetch_outcomes_batch", return_value={match_id: mock_outcome}
    )

    mock_stale_matches = mocker.patch.object(mock_stale_match_service, "run_stream_cleaning_cycle", return_value=[])

    # create
    provider = CompletionDataProvider(mock_redis_service, mock_stale_match_service)

    # ACT
    result = await provider.get_work_items()

    # ASSERT
    assert len(result) == 1

    mock_fetch_matches.assert_awaited_once()
    mock_fetch_outcome.assert_awaited_once()
    mock_stale_matches.assert_awaited_once()

    actual_work_item = result[0]

    # Check that it returns ConsumedEvent[CompletedMatchPayload]
    assert isinstance(actual_work_item, ConsumedEvent)
    assert actual_work_item.event_id == event_id
    assert actual_work_item.payload.match_outcome == mock_outcome
    assert actual_work_item.match_id == match_id


@pytest.mark.asyncio
async def test_get_work_items_no_events(mock_redis_service, mock_stale_match_service, mocker) -> None:
    # ARRANGE
    mock_fetch_matches = mocker.patch.object(mock_redis_service, "fetch_matches_for_completion", return_value=[])
    mock_stale = mocker.patch.object(mock_stale_match_service, "run_stream_cleaning_cycle", return_value=[])

    provider = CompletionDataProvider(mock_redis_service, mock_stale_match_service)

    # ACT
    result = await provider.get_work_items()

    # ASSERT
    assert len(result) == 0
    mock_fetch_matches.assert_awaited_once()
    # Recovery path is independent: it still runs even with no new events.
    mock_stale.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_work_items_no_outcomes(mock_redis_service, mock_stale_match_service, mocker) -> None:
    # ARRANGE
    match_id = 12345
    event_id = _recent_id()

    consumed_event = ConsumedEvent[CompletionPayload](
        match_id=match_id, event_id=event_id, payload=CompletionPayload(match_id=match_id, radiant_win=True)
    )

    mock_fetch_matches = mocker.patch.object(
        mock_redis_service, "fetch_matches_for_completion", return_value=[consumed_event]
    )

    # Mock FetchOutcomeService to return empty outcomes
    mock_fetch_outcome = mocker.patch(f"{F_PATH}.FetchOutcomeService.fetch_outcomes_batch", return_value={})
    mock_stale = mocker.patch.object(mock_stale_match_service, "run_stream_cleaning_cycle", return_value=[])

    provider = CompletionDataProvider(mock_redis_service, mock_stale_match_service)

    # ACT
    result = await provider.get_work_items()

    # ASSERT
    assert len(result) == 0  # Should return empty when no outcomes available
    mock_fetch_matches.assert_awaited_once()
    mock_fetch_outcome.assert_awaited_once()
    # No fresh outcomes must NOT short-circuit the recovery path.
    mock_stale.assert_awaited_once()


@pytest.mark.asyncio
async def test_stale_sweep_runs_when_fresh_fetch_fails(mock_redis_service, mock_stale_match_service, mocker) -> None:
    """A failure in the fresh path must not stop the independent stale recovery path."""
    # ARRANGE
    recovered = ConsumedEvent(match_id=999, event_id="stale_1", payload=CompletedMatchPayload(match_outcome=False))

    mocker.patch.object(mock_redis_service, "fetch_matches_for_completion", side_effect=RuntimeError("redis blip"))
    mock_stale = mocker.patch.object(mock_stale_match_service, "run_stream_cleaning_cycle", return_value=[recovered])

    provider = CompletionDataProvider(mock_redis_service, mock_stale_match_service)

    # ACT
    result = await provider.get_work_items()

    # ASSERT — fresh path swallowed its error, stale path still ran and contributed.
    mock_stale.assert_awaited_once()
    assert result == [recovered]


@pytest.mark.asyncio
async def test_aged_events_skip_free_feed(mock_redis_service, mock_stale_match_service, mocker) -> None:
    """Aged pending matches are excluded from the free-feed lookup (left for the paid stale
    path), so they can't widen the id-range and burn the free quota."""
    # ARRANGE — one fresh, one aged.
    fresh = ConsumedEvent[CompletionPayload](
        match_id=111, event_id=_recent_id(), payload=CompletionPayload(match_id=111, radiant_win=True)
    )
    aged = ConsumedEvent[CompletionPayload](
        match_id=222, event_id=_aged_id(), payload=CompletionPayload(match_id=222, radiant_win=True)
    )
    mocker.patch.object(mock_redis_service, "fetch_matches_for_completion", return_value=[fresh, aged])
    mock_fetch_outcome = mocker.patch(f"{F_PATH}.FetchOutcomeService.fetch_outcomes_batch", return_value={111: True})
    mocker.patch.object(mock_stale_match_service, "run_stream_cleaning_cycle", return_value=[])

    provider = CompletionDataProvider(mock_redis_service, mock_stale_match_service)

    # ACT
    result = await provider.get_work_items()

    # ASSERT — only the fresh match was sent to the free feed.
    mock_fetch_outcome.assert_awaited_once_with([111])
    assert len(result) == 1
    assert result[0].match_id == 111


@pytest.mark.asyncio
async def test_all_aged_events_skip_free_call(mock_redis_service, mock_stale_match_service, mocker) -> None:
    """When every pending event is aged, the free feed is not called at all (zero free quota
    spent); the stale path still runs."""
    # ARRANGE
    aged = ConsumedEvent[CompletionPayload](
        match_id=222, event_id=_aged_id(), payload=CompletionPayload(match_id=222, radiant_win=True)
    )
    mocker.patch.object(mock_redis_service, "fetch_matches_for_completion", return_value=[aged])
    mock_fetch_outcome = mocker.patch(f"{F_PATH}.FetchOutcomeService.fetch_outcomes_batch", return_value={})
    mock_stale = mocker.patch.object(mock_stale_match_service, "run_stream_cleaning_cycle", return_value=[])

    provider = CompletionDataProvider(mock_redis_service, mock_stale_match_service)

    # ACT
    result = await provider.get_work_items()

    # ASSERT — no free call for an all-aged batch; recovery path still ran.
    mock_fetch_outcome.assert_not_awaited()
    mock_stale.assert_awaited_once()
    assert result == []


"""
Todo:
# test_invalid_outcome_map_return_empty_list
# test_empty_results_from_redis_return_empty_list
"""
