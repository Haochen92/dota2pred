import pytest
from dota_oracle_common.constants.redis_constants import COMPLETION_GROUP, STREAM_PENDING_COMPLETION
from dota_oracle_common.models.redis.schema import ConsumedEvent, CompletedMatchPayload

F_PATH = "live_orchestrator_app.completion.completion_orchestrator"


@pytest.mark.asyncio
async def test_run_completion_cycle_successfully(
    completion_orchestrator, mocker, completed_match_payload_factory, task_result_factory
) -> None:
    # ARRANGE
    payload = completed_match_payload_factory.build()
    work_item = ConsumedEvent[CompletedMatchPayload](match_id=12345, event_id="event_123", payload=payload)

    mock_task_results = task_result_factory.build(key=work_item.event_id, inputs=work_item, outcome=True)

    mock_get_work_items = mocker.patch.object(
        completion_orchestrator.data_provider, "get_work_items", return_value=[work_item]
    )
    mock_task_runner = mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently", return_value=[mock_task_results])
    mock_mark_as_completed = mocker.patch.object(completion_orchestrator.redis, "mark_match_as_completed")

    # ACT
    result = await completion_orchestrator.run_completion_cycle()

    # ASSERT
    assert result == 1

    mock_get_work_items.assert_awaited_once_with("consumer_one")
    mock_task_runner.assert_awaited_once()
    mock_mark_as_completed.assert_awaited_once_with(match_id=work_item.match_id, event_id_to_ack=work_item.event_id)


@pytest.mark.asyncio
async def test_run_completion_cycle_no_work_items(completion_orchestrator, mocker) -> None:
    # ARRANGE
    mock_get_work_items = mocker.patch.object(completion_orchestrator.data_provider, "get_work_items", return_value=[])
    mock_task_runner = mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently")
    mock_mark_as_completed = mocker.patch.object(completion_orchestrator.redis, "mark_match_as_completed")

    # ACT
    result = await completion_orchestrator.run_completion_cycle()

    # ASSERT
    assert result == 0

    mock_get_work_items.assert_awaited_once_with("consumer_one")
    mock_task_runner.assert_not_called()
    mock_mark_as_completed.assert_not_called()


@pytest.mark.asyncio
async def test_run_completion_cycle_one_failure(
    completion_orchestrator, mocker, completed_match_payload_factory, task_result_factory
) -> None:
    # ARRANGE
    payload = completed_match_payload_factory.build()
    work_item = ConsumedEvent[CompletedMatchPayload](match_id=12345, event_id="event_123", payload=payload)

    mock_error = ValueError("Processing failed")
    mock_task_results = task_result_factory.build(key=work_item.event_id, inputs=work_item, outcome=mock_error)

    mock_get_work_items = mocker.patch.object(
        completion_orchestrator.data_provider, "get_work_items", return_value=[work_item]
    )
    mock_task_runner = mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently", return_value=[mock_task_results])
    mock_handle_failure = mocker.patch.object(completion_orchestrator.redis, "handle_processing_failure")
    mock_mark_as_completed = mocker.patch.object(completion_orchestrator.redis, "mark_match_as_completed")

    # ACT
    result = await completion_orchestrator.run_completion_cycle()

    # ASSERT
    assert result == 0

    mock_get_work_items.assert_awaited_once_with("consumer_one")
    mock_task_runner.assert_awaited_once()
    mock_mark_as_completed.assert_not_called()
    mock_handle_failure.assert_awaited_once_with(
        consumer_group=COMPLETION_GROUP,
        event_stream=STREAM_PENDING_COMPLETION,
        error=mock_error,
        event_data=work_item,
        event_id=work_item.event_id,
    )


@pytest.mark.asyncio
async def test_run_completion_cycle_mixed_results(
    completion_orchestrator, mocker, completed_match_payload_factory, task_result_factory
) -> None:
    # ARRANGE
    payload1 = completed_match_payload_factory.build()
    payload2 = completed_match_payload_factory.build()

    work_item1 = ConsumedEvent[CompletedMatchPayload](match_id=12345, event_id="event_123", payload=payload1)
    work_item2 = ConsumedEvent[CompletedMatchPayload](match_id=67890, event_id="event_456", payload=payload2)

    mock_error = RuntimeError("Second processing failed")

    # First task succeeds, second fails
    mock_task_results = [
        task_result_factory.build(key=work_item1.event_id, inputs=work_item1, outcome=True),
        task_result_factory.build(key=work_item2.event_id, inputs=work_item2, outcome=mock_error),
    ]

    mock_get_work_items = mocker.patch.object(
        completion_orchestrator.data_provider, "get_work_items", return_value=[work_item1, work_item2]
    )
    mock_task_runner = mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently", return_value=mock_task_results)
    mock_handle_failure = mocker.patch.object(completion_orchestrator.redis, "handle_processing_failure")
    mock_mark_as_completed = mocker.patch.object(completion_orchestrator.redis, "mark_match_as_completed")

    # ACT
    result = await completion_orchestrator.run_completion_cycle()

    # ASSERT
    assert result == 1  # Only one success

    mock_get_work_items.assert_awaited_once_with("consumer_one")
    mock_task_runner.assert_awaited_once()

    # One success, one failure
    mock_mark_as_completed.assert_awaited_once_with(match_id=work_item1.match_id, event_id_to_ack=work_item1.event_id)
    mock_handle_failure.assert_awaited_once_with(
        consumer_group=COMPLETION_GROUP,
        event_stream=STREAM_PENDING_COMPLETION,
        error=mock_error,
        event_data=work_item2,
        event_id=work_item2.event_id,
    )
