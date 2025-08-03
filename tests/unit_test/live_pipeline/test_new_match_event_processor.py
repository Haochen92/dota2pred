import pytest

F_PATH = "live_orchestrator_app.data_fetching.new_match_event_processor"


@pytest.mark.asyncio
async def test_process_event_successfully(
    new_match_event_processor, new_match_work_item_factory, match_table_factory, mocker
) -> None:
    work_item = new_match_work_item_factory.build()
    expected_transformed_match = match_table_factory.build(match_id=work_item.match_id)

    mock_parser = mocker.patch(f"{F_PATH}.parse_live_league_games", return_value=[expected_transformed_match])

    mock_insert_method = mocker.patch(
        f"{F_PATH}.MatchRepository.insert_match_details",
        autospec=True,  # Ensures it's an AsyncMock and checks the signature
    )
    # ACT
    await new_match_event_processor.process_event(work_item)

    # ASSERT
    mock_parser.assert_awaited_once_with([work_item.live_match_data])
    # The method is called with self (repo instance) as first arg, then the match data
    assert mock_insert_method.await_count == 1
    call_args = mock_insert_method.await_args_list[0]
    assert call_args[0][1] == [expected_transformed_match]  # Second argument (first is self)
