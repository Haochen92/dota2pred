import pytest
F_PATH = 'dota_oracle.live_pipeline.feature_engineering.feature_engineering_data_provider'

@pytest.mark.asyncio
async def test_get_work_items_successfully(feature_engineering_data_provider, mocker, stream_match_event_data_factory, match_table_factory):
    
    stream_event_data_1 = stream_match_event_data_factory.build()
    stream_event_data_2 = stream_match_event_data_factory.build()
    
    mock_events_dict = {
        'event_1': stream_event_data_1,
        'event_2': stream_event_data_2
    }
    
    match_id_1 = stream_event_data_1.match_id
    match_id_2 = stream_event_data_2.match_id
    
    mock_data_lookup = {
        match_id_1: match_table_factory.build(match_id=match_id_1),
        match_id_2: match_table_factory.build(match_id=match_id_2)
    }
    
    # Mock methods
    mock_redis = feature_engineering_data_provider.redis
    mock_redis.fetch_new_matches_for_feature_eng.return_value = mock_events_dict
    
    mock_validate_events = mocker.patch.object(
        feature_engineering_data_provider,
        '_validate_events',
        return_value=mock_events_dict
    )
    
    mock_fetch_match_details = mocker.patch.object(
        feature_engineering_data_provider,
        '_fetch_match_details',
        return_value=mock_data_lookup
    )
    
    # ACT
    actual_work_items = await feature_engineering_data_provider.get_work_items()
    
    # ASSERT
    assert len(actual_work_items) == 2, f"expected 2, got {len(actual_work_items)}"
    
    mock_redis.fetch_new_matches_for_feature_eng.assert_awaited_once()
    mock_validate_events.assert_called_once_with(mock_events_dict)
    mock_fetch_match_details.assert_awaited_once_with(mock_events_dict)
    
    
    
@pytest.mark.asyncio
async def test_fetch_match_details_successfully(
    feature_engineering_data_provider, 
    mock_match_repository, 
    mocker,
    stream_match_event_data_factory,
    match_table_factory
):
    stream_event_data_1 = stream_match_event_data_factory.build()
    stream_event_data_2 = stream_match_event_data_factory.build()
    
    mock_events_dict = {
        'event_1': stream_event_data_1,
        'event_2': stream_event_data_2
    }
    
    mock_match_details_list = [
        match_table_factory.build(match_id=stream_event_data_1.match_id),
        match_table_factory.build(match_id=stream_event_data_2.match_id)
    ]
    
    mocker.patch(f"{F_PATH}.MatchRepository", return_value=mock_match_repository)
    
    mock_get_match_details = mocker.patch.object(
        mock_match_repository,
        'get_match_details', 
        return_value=mock_match_details_list
    )
    
    # Act
    match_data_lookup = await feature_engineering_data_provider._fetch_match_details(mock_events_dict)
    
    # ASSERT
    assert len(match_data_lookup) == 2
    
    mock_get_match_details.assert_awaited_once()
    
    
    
    
