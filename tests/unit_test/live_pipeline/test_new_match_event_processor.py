import pytest
from unittest.mock import AsyncMock

F_PATH = "live_orchestrator_app.data_fetching.new_match_event_processor"


@pytest.mark.asyncio
async def test_process_event_successfully(
    new_match_event_processor,
    ongoing_league_game_factory,
    match_table_factory,
    mock_db_session_factory,
    mock_async_session,
    mocker,
) -> None:
    # ARRANGE
    ongoing_match = ongoing_league_game_factory.build()
    expected_transformed_match = match_table_factory.build(match_id=ongoing_match.match_id)

    mock_parser = mocker.patch(f"{F_PATH}.parse_live_league_games", return_value=[expected_transformed_match])

    mock_insert_method = mocker.patch(
        f"{F_PATH}.MatchRepository.insert_match_details",
        autospec=True,
    )

    # Use the provided mock_db_session_factory
    new_match_event_processor.db_session_factory = mock_db_session_factory

    # Mock the transaction context
    mock_transaction = AsyncMock()
    mock_async_session.begin.return_value = mock_transaction

    # ACT
    result = await new_match_event_processor.process_event(ongoing_match)

    # ASSERT
    assert result == expected_transformed_match
    mock_parser.assert_awaited_once_with([ongoing_match])

    # The method is called with self (repo instance) as first arg, then the match data
    assert mock_insert_method.await_count == 1
    call_args = mock_insert_method.await_args_list[0]
    assert call_args[0][1] == [expected_transformed_match]  # Second argument (first is self)


@pytest.mark.asyncio
async def test_process_event_transform_fails(
    new_match_event_processor, ongoing_league_game_factory, mock_db_session_factory, mocker
) -> None:
    # ARRANGE
    ongoing_match = ongoing_league_game_factory.build()
    transform_error = ValueError("Transform failed")

    mock_parser = mocker.patch(f"{F_PATH}.parse_live_league_games", side_effect=transform_error)
    mock_insert_method = mocker.patch(f"{F_PATH}.MatchRepository.insert_match_details")

    new_match_event_processor.db_session_factory = mock_db_session_factory

    # ACT & ASSERT
    with pytest.raises(ValueError, match="Transform failed"):
        await new_match_event_processor.process_event(ongoing_match)

    mock_parser.assert_awaited_once_with([ongoing_match])
    mock_insert_method.assert_not_called()


@pytest.mark.asyncio
async def test_process_event_transform_returns_empty(
    new_match_event_processor, ongoing_league_game_factory, mock_db_session_factory, mocker
) -> None:
    # ARRANGE
    ongoing_match = ongoing_league_game_factory.build()

    mock_parser = mocker.patch(f"{F_PATH}.parse_live_league_games", return_value=[])
    mock_insert_method = mocker.patch(f"{F_PATH}.MatchRepository.insert_match_details")

    new_match_event_processor.db_session_factory = mock_db_session_factory

    # ACT & ASSERT
    with pytest.raises(ValueError, match=f"Failed to transform match data for match {ongoing_match.match_id}"):
        await new_match_event_processor.process_event(ongoing_match)

    mock_parser.assert_awaited_once_with([ongoing_match])
    mock_insert_method.assert_not_called()


@pytest.mark.asyncio
async def test_process_event_store_fails(
    new_match_event_processor,
    ongoing_league_game_factory,
    match_table_factory,
    mock_db_session_factory,
    mock_async_session,
    mocker,
) -> None:
    # ARRANGE
    ongoing_match = ongoing_league_game_factory.build()
    expected_transformed_match = match_table_factory.build(match_id=ongoing_match.match_id)
    store_error = Exception("Store failed")

    mock_parser = mocker.patch(f"{F_PATH}.parse_live_league_games", return_value=[expected_transformed_match])
    mock_insert_method = mocker.patch(f"{F_PATH}.MatchRepository.insert_match_details", side_effect=store_error)

    # Use the provided mock_db_session_factory
    new_match_event_processor.db_session_factory = mock_db_session_factory

    # Mock the transaction context
    mock_transaction = AsyncMock()
    mock_async_session.begin.return_value = mock_transaction

    # ACT & ASSERT
    with pytest.raises(Exception, match="Store failed"):
        await new_match_event_processor.process_event(ongoing_match)

    mock_parser.assert_awaited_once_with([ongoing_match])
    mock_insert_method.assert_awaited_once()
