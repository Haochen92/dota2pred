import pytest
from ...factories.unit_test_factory import CompletionWorkItemFactory, TaskResultFactory
from dota_oracle.constants.redis_constants import COMPLETION_GROUP, STREAM_PENDING_COMPLETION

F_PATH = 'dota_oracle.live_pipeline.completion.completion_orchestrator'

pytest.mark.asyncio
async def test_run_completion_cycle_successfully(mocker, completion_orchestrator):
    
    # ARRANGE 
    mock_work_items = CompletionWorkItemFactory.build()
    mock_task_results = TaskResultFactory.build(
        key=mock_work_items.event_id,
        exception=None
    )
    
    mock_get_work_items = mocker.patch.object(completion_orchestrator.data_provider, 'get_work_items', return_value=[mock_work_items])
    mock_task_runner = mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently", return_value=[mock_task_results])
    mock_mark_as_completed = mocker.patch.object(completion_orchestrator.redis, 'mark_match_as_completed')
    
    
    # ACT
    result = await completion_orchestrator.run_completion_cycle()
    
    # ASSERT
    assert result == 1
    
    mock_get_work_items.assert_awaited_once()
    mock_task_runner.assert_awaited_once()
    mock_mark_as_completed.assert_awaited_once()
    
@pytest.mark.asyncio
async def test_run_completion_cycle_one_failure(mocker, completion_orchestrator):
    # Arrange
    mock_work_items = CompletionWorkItemFactory.build()
    mock_error = ValueError()
    mock_task_results = TaskResultFactory.build(
        key=mock_work_items.event_id,
        exception=mock_error
    )
    
    mock_get_work_items = mocker.patch.object(completion_orchestrator.data_provider, 'get_work_items', return_value=[mock_work_items])
    mock_task_runner = mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently", return_value=[mock_task_results])
    mock_redis_call = mocker.patch.object(completion_orchestrator.redis, 'handle_processing_failure')
    
    # ACT
    result = await completion_orchestrator.run_completion_cycle()
    
    # ASSERT
    assert result == 0
    
    mock_get_work_items.assert_awaited_once()
    mock_task_runner.assert_awaited_once()
    mock_redis_call.assert_awaited_once_with(
        consumer_group=COMPLETION_GROUP,
        event_stream=STREAM_PENDING_COMPLETION,
        error=mock_error,
        event_data=mock_work_items.event_data,
        event_id=mock_work_items.event_id
    )