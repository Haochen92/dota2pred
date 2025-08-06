import pytest
from unittest.mock import AsyncMock
from dota_oracle_common.models.redis.schema import ConsumedEvent, CompletedMatchPayload
from dota_oracle_common.models.match import MatchOutcomeTable
from live_orchestrator_app.completion.completion_event_processor import CompletionEventProcessor

F_PATH = "live_orchestrator_app.completion.completion_event_processor"


@pytest.mark.asyncio
async def test_process_events_successfully(
    completion_event_processor: CompletionEventProcessor,
    mocker,
    completed_match_payload_factory,
    mock_match_repository,
    mock_db_session_factory,
    mock_async_session,
) -> None:
    # ARRANGE
    payload = completed_match_payload_factory.build()
    work_item = ConsumedEvent[CompletedMatchPayload](match_id=12345, event_id="event_123", payload=payload)

    mocker.patch(f"{F_PATH}.MatchRepository", return_value=mock_match_repository)
    mock_history_updater = mocker.patch.object(completion_event_processor.history_updater, "update_histories")

    # Use the provided mock_db_session_factory
    completion_event_processor.db_session_factory = mock_db_session_factory

    # Mock the transaction context
    mock_transaction = AsyncMock()
    mock_async_session.begin.return_value = mock_transaction

    # ACT
    result = await completion_event_processor.process_events(work_item)

    # ASSERT
    assert result is True

    expected_outcome_instance = MatchOutcomeTable(
        match_id=work_item.match_id, radiant_win=work_item.payload.match_outcome
    )

    mock_match_repository.insert_match_outcome.assert_awaited_once()
    # Check if the call was made with expected data (comparing dict representations due to object equality)
    call_args = mock_match_repository.insert_match_outcome.call_args[0][0]
    assert len(call_args) == 1
    assert call_args[0].match_id == expected_outcome_instance.match_id
    assert call_args[0].radiant_win == expected_outcome_instance.radiant_win

    mock_history_updater.assert_awaited_once_with(completion_event_processor.db_session_factory, work_item.match_id)


@pytest.mark.asyncio
async def test_process_events_match_repository_fails(
    completion_event_processor: CompletionEventProcessor,
    mocker,
    completed_match_payload_factory,
    mock_match_repository,
    mock_db_session_factory,
    mock_async_session,
) -> None:
    # ARRANGE
    payload = completed_match_payload_factory.build()
    work_item = ConsumedEvent[CompletedMatchPayload](match_id=12345, event_id="event_123", payload=payload)

    db_error = Exception("Database error")
    mock_match_repository.insert_match_outcome.side_effect = db_error
    mocker.patch(f"{F_PATH}.MatchRepository", return_value=mock_match_repository)
    mock_history_updater = mocker.patch.object(completion_event_processor.history_updater, "update_histories")

    # Use the provided mock_db_session_factory
    completion_event_processor.db_session_factory = mock_db_session_factory

    # Mock the transaction context
    mock_transaction = AsyncMock()
    mock_async_session.begin.return_value = mock_transaction

    # ACT & ASSERT
    with pytest.raises(Exception, match="Database error"):
        await completion_event_processor.process_events(work_item)

    mock_match_repository.insert_match_outcome.assert_awaited_once()
    mock_history_updater.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_events_history_updater_fails(
    completion_event_processor: CompletionEventProcessor,
    mocker,
    completed_match_payload_factory,
    mock_match_repository,
    mock_db_session_factory,
    mock_async_session,
) -> None:
    # ARRANGE
    payload = completed_match_payload_factory.build()
    work_item = ConsumedEvent[CompletedMatchPayload](match_id=12345, event_id="event_123", payload=payload)

    history_error = Exception("History update error")
    mocker.patch(f"{F_PATH}.MatchRepository", return_value=mock_match_repository)
    mock_history_updater = mocker.patch.object(
        completion_event_processor.history_updater, "update_histories", side_effect=history_error
    )

    # Use the provided mock_db_session_factory
    completion_event_processor.db_session_factory = mock_db_session_factory

    # Mock the transaction context
    mock_transaction = AsyncMock()
    mock_async_session.begin.return_value = mock_transaction

    # ACT & ASSERT
    with pytest.raises(Exception, match="History update error"):
        await completion_event_processor.process_events(work_item)

    mock_match_repository.insert_match_outcome.assert_awaited_once()
    mock_history_updater.assert_awaited_once()
