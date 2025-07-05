import pytest
from unittest.mock import AsyncMock


from dota_oracle_common.repositories.match_repository import MatchRepository
from live_orchestrator_app.completion.completion_event_processor import CompletionEventProcessor

F_PATH = "live_orchestrator_app.completion.completion_event_processor"


@pytest.mark.asyncio
async def test_process_events_successfully(
    completion_event_processor: CompletionEventProcessor, mock_async_session, mocker, completion_work_item_factory
) -> None:
    # ARRANGE
    mock_work_item = completion_work_item_factory.build()
    mock_repository = AsyncMock(spec=MatchRepository)

    mocker.patch(f"{F_PATH}.MatchRepository", return_value=mock_repository)

    mocked_async_session_class = mocker.patch(f"{F_PATH}.AsyncSession")
    mocked_async_session_class.return_value.__aenter__.return_value = mock_async_session
    mocked_async_session_class.return_value.__aexit__.return_value = None

    mock_update_outcome = mocker.patch.object(completion_event_processor, "_update_match_outcome")
    mock_update_history = mocker.patch.object(completion_event_processor.history_updater, "update_histories")

    # ACT
    await completion_event_processor.process_events(mock_work_item)

    # ASSERT
    mock_update_outcome.assert_awaited_once_with(
        match_repository=mock_repository,
        match_id=mock_work_item.event_data.match_id,
        match_outcome=mock_work_item.outcome,
    )

    mock_update_history.assert_awaited_once_with(mock_async_session, mock_work_item.event_data.match_id)
