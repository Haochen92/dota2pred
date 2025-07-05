import pytest

from live_orchestrator_app.completion.completion_data_provider import CompletionDataProvider

F_PATH = "live_orchestrator_app.completion.completion_data_provider"

@pytest.mark.asyncio
async def test_get_work_items_successfully(mock_redis_service, stream_match_event_data_factory, mocker):
    # ARRANGE
    match_id = 12345
    event_id = "event_123"
    event_data = stream_match_event_data_factory.build(match_id=match_id)
    mock_outcome = True
    
    # Mock methods
    mock_fetch_matches = mocker.patch.object(
        mock_redis_service, 
        'fetch_matches_pending_completion',
        return_value={event_id: event_data}
    )
    
    mock_fetch_outcome = mocker.patch(
        f'{F_PATH}.FetchOutcomeService.fetch_outcomes_batch',
        return_value={match_id: mock_outcome}
    )
    
    # create
    provider = CompletionDataProvider(mock_redis_service)
    
    # ACT
    
    result = await provider.get_work_items()
    
    
    # ASSERT
    assert len(result) == 1
    
    mock_fetch_matches.assert_awaited_once()
    mock_fetch_outcome.assert_awaited_once()
    
    actual_work_item = result[0]
    
    assert actual_work_item.event_id == event_id
    assert actual_work_item.outcome == mock_outcome
    assert actual_work_item.event_data == event_data
    
    
"""
Todo:
# test_invalid_outcome_map_return_empty_list
# test_empty_results_from_redis_return_empty_list
"""

