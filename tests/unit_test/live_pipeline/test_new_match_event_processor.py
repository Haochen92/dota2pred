import pytest

F_PATH = "live_orchestrator_app.data_fetching.new_match_event_processor"


@pytest.mark.asyncio
async def test_process_event_successfully(
    new_match_event_processor, mock_async_session, mocker, new_match_work_item_factory, match_table_factory
) -> None:
    work_item = new_match_work_item_factory.build()
    match_details = match_table_factory.build(match_id=work_item.match_id)

    mock_async_session_class = mocker.patch(f"{F_PATH}.AsyncSession")
    mock_async_session_class.return_value.__aenter__.return_value = mock_async_session
    mock_async_session_class.return_value.__aexit__.return_value = None

    mock_transform_data = mocker.patch.object(
        new_match_event_processor, "_transform_match_data", return_value=match_details
    )
    mock_store_data = mocker.patch.object(new_match_event_processor, "_store_match_details")

    # ACT
    await new_match_event_processor.process_event(work_item)

    # ASSERT
    mock_transform_data.assert_awaited_once_with(work_item, mock_async_session)
    mock_store_data.assert_awaited_once_with(match_details, mock_async_session)
