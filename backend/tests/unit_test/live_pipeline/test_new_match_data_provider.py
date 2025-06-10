import pytest
from unittest.mock import AsyncMock

from ...factories.unit_test_factory import LiveLeagueGameFactory, NewMatchWorkItemFactory

@pytest.mark.asyncio
async def test_get_work_items_successfully(new_match_data_provider, mocker):
    # mock live_league_games
    mock_list_current_matches = LiveLeagueGameFactory.batch(3)
    
    mock_fetch_current_matches = mocker.patch.object(
        new_match_data_provider, 
        '_fetch_current_matches', 
        return_value=mock_list_current_matches
    )
    
    mock_filter_new_matches = mocker.patch.object(
        new_match_data_provider,
        '_filter_new_matches',
        return_value=mock_list_current_matches[:2] # filter the first 2 values
    )
    
    # ACT
    actual_work_items = await new_match_data_provider.get_work_items()
    
    # ASSERT
    assert len(actual_work_items) == 2
    
    mock_fetch_current_matches.assert_awaited_once()
    mock_filter_new_matches.assert_awaited_once_with(mock_list_current_matches)
    

@pytest.mark.asyncio
async def test_filter_new_matches_with_values(new_match_data_provider, mocker):
    mock_current_matches = LiveLeagueGameFactory.batch(5)
    mock_new_match_set = {match.match_id for match in mock_current_matches if match.match_id % 2 == 0}
    
    mock_get_new_match_set = mocker.patch.object(
        new_match_data_provider.redis, 
        'update_live_match_set_and_get_new',
        return_value=mock_new_match_set
    )
    
    # ACT
    actual_new_matches = await new_match_data_provider._filter_new_matches(mock_current_matches)
    
    # Assert
    assert len(actual_new_matches) == len(mock_new_match_set), f"Expected {len(mock_new_match_set)}, got {len(actual_new_matches)}"
    
    mock_get_new_match_set.assert_awaited_once()
    
    assert all([match.match_id in mock_new_match_set for match in actual_new_matches]) 