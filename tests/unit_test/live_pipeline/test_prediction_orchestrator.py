import pytest
from typing import Any, List
from dota_oracle_common.constants.redis_constants import PREDICTION_GROUP, STREAM_PENDING_PREDICTION
from dota_oracle_common.models.utils.schema import TaskResult, AsyncTask
from live_orchestrator_app.prediction.prediction_orchestrator import PredictionOrchestrator

F_PATH = "live_orchestrator_app.prediction.prediction_orchestrator"


@pytest.mark.asyncio
async def test_run_prediction_cycle_successfully(
    prediction_orchestrator: PredictionOrchestrator,
    prediction_payload_factory: Any,
    task_result_factory: Any,
    mocker: Any,
) -> None:
    # ARRANGE
    from dota_oracle_common.models.redis.schema import ConsumedEvent

    # Create mock ConsumedEvent[PredictionPayload] objects
    payload1 = prediction_payload_factory.build()
    payload2 = prediction_payload_factory.build()
    mock_work_items = [
        ConsumedEvent[type(payload1)](match_id=12345, event_id="event1", payload=payload1),
        ConsumedEvent[type(payload2)](match_id=67890, event_id="event2", payload=payload2),
    ]

    mock_get_work_items = mocker.patch.object(
        prediction_orchestrator.data_provider, "get_work_items", return_value=mock_work_items
    )

    # Mock TaskRunner.run_concurrently to return successful results for each work item
    async def mock_run_concurrently(tasks: List[AsyncTask]) -> List[TaskResult]:
        results = []
        for task in tasks:
            result = task_result_factory.build(
                key=task.key, inputs=task.inputs, exception=None, outcome="mock_prediction_result"
            )
            results.append(result)
        return results

    mock_task_runner = mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently", side_effect=mock_run_concurrently)
    mock_advance_match = mocker.patch.object(prediction_orchestrator.redis, "publish_prediction_to_completion")

    # ACT
    result = await prediction_orchestrator.run_prediction_cycle()

    # ASSERT
    assert result == 2

    mock_get_work_items.assert_awaited_once_with(prediction_orchestrator.consumer_name)
    mock_task_runner.assert_awaited_once()
    assert mock_advance_match.await_count == 2


@pytest.mark.asyncio
async def test_run_prediction_cycle_no_work_items(prediction_orchestrator: PredictionOrchestrator, mocker: Any) -> None:
    # ARRANGE
    mock_get_work_items = mocker.patch.object(prediction_orchestrator.data_provider, "get_work_items", return_value=[])
    mock_task_runner = mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently")

    # ACT
    result = await prediction_orchestrator.run_prediction_cycle()

    # ASSERT
    assert result == 0

    mock_get_work_items.assert_awaited_once_with(prediction_orchestrator.consumer_name)
    mock_task_runner.assert_not_awaited()


@pytest.mark.asyncio
async def test_run_prediction_cycle_one_failure(
    prediction_orchestrator: PredictionOrchestrator,
    prediction_payload_factory: Any,
    task_result_factory: Any,
    mocker: Any,
) -> None:
    # ARRANGE
    from dota_oracle_common.models.redis.schema import ConsumedEvent

    payload1 = prediction_payload_factory.build()
    payload2 = prediction_payload_factory.build()
    mock_work_items = [
        ConsumedEvent[type(payload1)](match_id=12345, event_id="event1", payload=payload1),
        ConsumedEvent[type(payload2)](match_id=67890, event_id="event2", payload=payload2),
    ]
    mock_error = ValueError("Prediction failed")

    mock_get_work_items = mocker.patch.object(
        prediction_orchestrator.data_provider, "get_work_items", return_value=mock_work_items
    )

    # Mock TaskRunner.run_concurrently to return mixed results
    async def mock_run_concurrently(tasks: List[AsyncTask]) -> List[TaskResult]:
        results = []
        for i, task in enumerate(tasks):
            if i == 0:  # First task succeeds
                result = task_result_factory.build(
                    key=task.key, inputs=task.inputs, exception=None, outcome="mock_prediction_result"
                )
            else:  # Second task fails
                result = task_result_factory.build(key=task.key, inputs=task.inputs, outcome=mock_error)
            results.append(result)
        return results

    mock_task_runner = mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently", side_effect=mock_run_concurrently)
    mock_advance_match = mocker.patch.object(prediction_orchestrator.redis, "publish_prediction_to_completion")
    mock_handle_failure = mocker.patch.object(prediction_orchestrator.redis, "handle_processing_failure")

    # ACT
    result = await prediction_orchestrator.run_prediction_cycle()

    # ASSERT
    assert result == 1  # Only one successful

    mock_get_work_items.assert_awaited_once_with(prediction_orchestrator.consumer_name)
    mock_task_runner.assert_awaited_once()

    # Verify success and failure handling
    assert mock_advance_match.await_count == 1
    assert mock_handle_failure.await_count == 1


@pytest.mark.asyncio
async def test_run_prediction_cycle_all_failures(
    prediction_orchestrator: PredictionOrchestrator,
    prediction_payload_factory: Any,
    task_result_factory: Any,
    mocker: Any,
) -> None:
    # ARRANGE
    from dota_oracle_common.models.redis.schema import ConsumedEvent

    payload1 = prediction_payload_factory.build()
    payload2 = prediction_payload_factory.build()
    mock_work_items = [
        ConsumedEvent[type(payload1)](match_id=12345, event_id="event1", payload=payload1),
        ConsumedEvent[type(payload2)](match_id=67890, event_id="event2", payload=payload2),
    ]
    mock_error1 = ValueError("First prediction failed")
    mock_error2 = RuntimeError("Second prediction failed")
    mock_task_results = [
        task_result_factory.build(key=mock_work_items[0].event_id, inputs=mock_work_items[0], outcome=mock_error1),
        task_result_factory.build(key=mock_work_items[1].event_id, inputs=mock_work_items[1], outcome=mock_error2),
    ]

    mock_get_work_items = mocker.patch.object(
        prediction_orchestrator.data_provider, "get_work_items", return_value=mock_work_items
    )
    mock_task_runner = mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently", return_value=mock_task_results)
    mock_advance_match = mocker.patch.object(prediction_orchestrator.redis, "publish_prediction_to_completion")
    mock_handle_failure = mocker.patch.object(prediction_orchestrator.redis, "handle_processing_failure")

    # ACT
    result = await prediction_orchestrator.run_prediction_cycle()

    # ASSERT
    assert result == 0  # No successful predictions

    mock_get_work_items.assert_awaited_once_with(prediction_orchestrator.consumer_name)
    mock_task_runner.assert_awaited_once()
    mock_advance_match.assert_not_awaited()

    # Verify both failures were handled
    assert mock_handle_failure.await_count == 2
    mock_handle_failure.assert_any_await(
        event_data=mock_work_items[0],
        event_id=mock_work_items[0].event_id,
        error=mock_error1,
        consumer_group=PREDICTION_GROUP,
        event_stream=STREAM_PENDING_PREDICTION,
    )
    mock_handle_failure.assert_any_await(
        event_data=mock_work_items[1],
        event_id=mock_work_items[1].event_id,
        error=mock_error2,
        consumer_group=PREDICTION_GROUP,
        event_stream=STREAM_PENDING_PREDICTION,
    )


@pytest.mark.asyncio
async def test_run_prediction_cycle_creates_correct_async_tasks(
    prediction_orchestrator: PredictionOrchestrator,
    prediction_payload_factory: Any,
    task_result_factory: Any,
    mocker: Any,
) -> None:
    # ARRANGE
    from dota_oracle_common.models.redis.schema import ConsumedEvent

    payload = prediction_payload_factory.build()
    mock_work_items = [ConsumedEvent[type(payload)](match_id=12345, event_id="event1", payload=payload)]

    mocker.patch.object(prediction_orchestrator.data_provider, "get_work_items", return_value=mock_work_items)

    # Mock TaskRunner to capture the tasks passed to it
    captured_tasks = []

    async def capture_tasks(tasks: List[AsyncTask]) -> List[TaskResult]:
        captured_tasks.extend(tasks)
        return [
            task_result_factory.build(
                key=mock_work_items[0].event_id,
                inputs=mock_work_items[0],
                exception=None,
                outcome="mock_prediction_result",
            )
        ]

    mocker.patch(f"{F_PATH}.TaskRunner.run_concurrently", side_effect=capture_tasks)
    mocker.patch.object(prediction_orchestrator.redis, "publish_prediction_to_completion")

    # ACT
    await prediction_orchestrator.run_prediction_cycle()

    # ASSERT
    assert len(captured_tasks) == 1
    task = captured_tasks[0]
    assert task.key == mock_work_items[0].event_id
    # Note: We can't easily test the coroutine content without executing it


@pytest.mark.asyncio
async def test_run_prediction_cycle_with_custom_consumer_name(mocker: Any) -> None:
    # ARRANGE
    custom_consumer = "custom_prediction_consumer"
    mock_redis_service = mocker.AsyncMock()
    mock_data_provider = mocker.AsyncMock()
    mock_event_processor = mocker.AsyncMock()

    # Create orchestrator with custom consumer name

    orchestrator = PredictionOrchestrator(
        redis_service=mock_redis_service,
        data_provider=mock_data_provider,
        event_processor=mock_event_processor,
        consumer_name=custom_consumer,
    )

    mock_work_items: List[Any] = []
    mock_data_provider.get_work_items.return_value = mock_work_items

    # ACT
    result = await orchestrator.run_prediction_cycle()

    # ASSERT
    assert result == 0
    mock_data_provider.get_work_items.assert_awaited_once_with(custom_consumer)


def test_prediction_orchestrator_initialization(prediction_orchestrator: PredictionOrchestrator) -> None:
    # ASSERT
    assert prediction_orchestrator.consumer_name == "consumer_one"
    assert prediction_orchestrator.redis is not None
    assert prediction_orchestrator.data_provider is not None
    assert prediction_orchestrator.event_processor is not None
