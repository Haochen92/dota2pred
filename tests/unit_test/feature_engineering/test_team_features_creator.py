import pytest
from dota_oracle_common.models.features import TeamFeaturesTable

FUNCTION_FP = 'dota_oracle_pipeline.feature_engineering.team_features_creator'

@pytest.mark.asyncio
async def test_team_feature_success(
    team_feature_creator, 
    mock_async_session,
    mocker,
    match_table_factory,
):
    """
    Tests the happy path where a feature row is successfully created for a valid match.
    """
    # Arrange
    match_instance = match_table_factory.build(match_id=1001, radiant_name='Team Liquid', dire_name='Team Secret')
    
    # Mock called methods
    mocker.patch.object(team_feature_creator, '_calculate_team_win_rate', return_value=0.6) # version 3.8 auto creates asyncMock
    mocker.patch.object(team_feature_creator, '_calculate_matchup_win_rate', return_value=0.5)

    # Act
    result = await team_feature_creator.create_team_features(
        db_session=mock_async_session,
        match_instances=[match_instance]
    )
    
    # Assert
    assert len(result) == 1
    feature_row = result[0]
    
    assert isinstance(feature_row, TeamFeaturesTable)
    assert feature_row.match_id == 1001
    
    # Check if a sample feature was set correctly from the mocked result
    assert feature_row.radiant_win_rate == 0.6
    assert feature_row.dire_win_rate == 0.6
    assert feature_row.radiant_dire_matchup == 0.5
