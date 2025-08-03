import pytest


from dota_oracle_common.repositories.match_repository import MatchOutcomeTable
from live_orchestrator_app.completion.completion_event_processor import CompletionEventProcessor

F_PATH = "live_orchestrator_app.completion.completion_event_processor"


@pytest.mark.asyncio
async def test_process_events_successfully(
    completion_event_processor: CompletionEventProcessor, mocker, completion_work_item_factory, mock_match_repository
) -> None:
    # ARRANGE
    mock_work_item = completion_work_item_factory.build()
    mocker.patch(f"{F_PATH}.MatchRepository", return_value=mock_match_repository)

    mock_history_updater = mocker.patch.object(completion_event_processor.history_updater, "update_histories")

    # ACT
    await completion_event_processor.process_events(mock_work_item)

    expected_outcome_instance = MatchOutcomeTable(
        match_id=mock_work_item.event_data.match_id, radiant_win=mock_work_item.outcome
    )

    # ASSERT
    mock_match_repository.insert_match_outcome.assert_awaited_once()
    mock_match_repository.insert_match_outcome.assert_awaited_with([expected_outcome_instance])

    mock_history_updater.assert_awaited_once_with(
        completion_event_processor.db_session_factory, mock_work_item.event_data.match_id
    )
