import pytest
from dota_oracle_common.models.redis.schema import ConsumedEvent, CompletionPayload

from live_orchestrator_app.completion.completion_data_provider import CompletionDataProvider

F_PATH = "live_orchestrator_app.completion.completion_data_provider"


@pytest.mark.asyncio
async def test_get_work_items_successfully(mock_redis_service, mock_stale_match_service, mocker) -> None:
    # ARRANGE
    match_id = 12345
    event_id = "event_123"
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

    provider = CompletionDataProvider(mock_redis_service, mock_stale_match_service)

    # ACT
    result = await provider.get_work_items()

    # ASSERT
    assert len(result) == 0
    mock_fetch_matches.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_work_items_no_outcomes(mock_redis_service, mock_stale_match_service, mocker) -> None:
    # ARRANGE
    match_id = 12345
    event_id = "event_123"

    consumed_event = ConsumedEvent[CompletionPayload](
        match_id=match_id, event_id=event_id, payload=CompletionPayload(match_id=match_id, radiant_win=True)
    )

    mock_fetch_matches = mocker.patch.object(
        mock_redis_service, "fetch_matches_for_completion", return_value=[consumed_event]
    )

    # Mock FetchOutcomeService to return empty outcomes
    mock_fetch_outcome = mocker.patch(f"{F_PATH}.FetchOutcomeService.fetch_outcomes_batch", return_value={})

    provider = CompletionDataProvider(mock_redis_service, mock_stale_match_service)

    # ACT
    result = await provider.get_work_items()

    # ASSERT
    assert len(result) == 0  # Should return empty when no outcomes available
    mock_fetch_matches.assert_awaited_once()
    mock_fetch_outcome.assert_awaited_once()


"""
Todo:
# test_invalid_outcome_map_return_empty_list
# test_empty_results_from_redis_return_empty_list
"""
