import pytest
from unittest.mock import ANY
from datetime import datetime, timezone
from dota_oracle.models.features import PlayerHeroFeatureTable
from ...factories.repository_factories import MatchTableFactory
from dota_oracle.models.match import MatchTable

FUNCTION_FP = 'dota_oracle.feature_engineering.player_hero_features_creator'

@pytest.mark.asyncio
async def test_create_player_hero_features_success(
    player_hero_features_creator, 
    mocker,
    mock_task_result_factory,
):
    """
    Tests the happy path where a feature row is successfully created for a valid match.
    """
    # Arrange
    mock_session = mocker.AsyncMock()
    
    match_instance = MatchTableFactory.build(match_id=1001)
    
    # Mock the TaskRunner to return predictable results for each player
    mock_results = [
        mock_task_result_factory(key=f'player_hero_{i}_win_rate', result=0.6)
        for i in list(range(5)) + list(range(128, 133))
    ]
    
    # Patch the TaskRunner within the module where it's being used
    mocker.patch(
        f'{FUNCTION_FP}.TaskRunner.run_concurrently',
        return_value=mock_results
    )

    # Act
    result = await player_hero_features_creator.create_player_hero_features(
        session=mock_session,
        match_instances=[match_instance]
    )
    
    # Assert
    assert len(result) == 1
    feature_row = result[0]
    
    assert isinstance(feature_row, PlayerHeroFeatureTable)
    assert feature_row.match_id == 1001
    
    # Check if a sample feature was set correctly from the mocked result
    assert feature_row.player_hero_0_win_rate == 0.6
    assert feature_row.player_hero_128_win_rate == 0.6


# ✅ REWRITTEN: Using pytest.param with clean approach
@pytest.mark.asyncio
@pytest.mark.parametrize("missing_data", [
    pytest.param(
        {"match_id": 123, "slot_0_account_id": None}, 
        id="missing_account_id"
    ),
    pytest.param(
        {"match_id": 124, "slot_0_hero_id": None}, 
        id="missing_hero_id"
    ),
    pytest.param(
        {"match_id": 125, "start_time": None}, 
        id="missing_start_time"
    ),
])
async def test_create_features_skips_match_with_missing_data(
    player_hero_features_creator, 
    mocker,
    missing_data: dict
):
    """
    Tests that a match is skipped if essential data like account_id is missing.
    """
    # Arrange - Factory called at test time, fresh instance each run
    match_instance = MatchTableFactory.build(**missing_data)
    
    mock_session = mocker.AsyncMock()
    mock_logger_error = mocker.patch(f'{FUNCTION_FP}.logger.error')
    
    # Act
    result = await player_hero_features_creator.create_player_hero_features(
        session=mock_session,
        match_instances=[match_instance]
    )
    
    # Assert
    assert len(result) == 0, f"Expected 0 results, got {len(result)}"
    mock_logger_error.assert_called_once()


@pytest.mark.asyncio
async def test_create_features_handles_task_failure_gracefully(
    player_hero_features_creator, 
    mock_task_result_factory, 
    mocker
):
    """
    Tests that if a single win-rate calculation fails, it defaults to 0.5
    and the feature creation for the match still succeeds.
    """
    # Arrange
    mock_session = mocker.AsyncMock()
    match_instance = MatchTableFactory.build(match_id=789)
    
    # Mock results where one task fails and the others succeed
    mock_results = [
        mock_task_result_factory(key='player_hero_0_win_rate', result=0.75),
        mock_task_result_factory(key='player_hero_1_win_rate', exception=ValueError("Calculation failed!")),
    ] + [
        mock_task_result_factory(key=f'player_hero_{i}_win_rate', result=0.6)
        for i in list(range(2, 5)) + list(range(128, 133))
    ]
    
    mocker.patch(
        f'{FUNCTION_FP}.TaskRunner.run_concurrently',
        return_value=mock_results
    )
    mock_logger_warning = mocker.patch(f'{FUNCTION_FP}.logger.warning')
    
    # Act
    result = await player_hero_features_creator.create_player_hero_features(
        session=mock_session,
        match_instances=[match_instance]
    )
    
    # Assert
    assert len(result) == 1
    feature_row = result[0]
    assert feature_row.match_id == 789
    
    # The successful task's result is used
    assert feature_row.player_hero_0_win_rate == 0.75
    # The failed task's result is the default fallback value
    assert feature_row.player_hero_1_win_rate == 0.5
    # A logger warning was issued for the failed task
    mock_logger_warning.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("win_rate_scenario", [
    pytest.param([], 0.5, id="no_history_defaults_to_half"),
    pytest.param([True, True], 1.0, id="all_wins_perfect_rate"),
    pytest.param([False, False, False], 0.0, id="all_losses_zero_rate"),
    pytest.param([True, False, True], 2/3, id="mixed_results_calculated"),
])
async def test_calculate_win_rate_logic(
    player_hero_features_creator, 
    mocker, 
    win_rate_scenario
):
    """
    Tests the _calculate_win_rate helper method's logic directly.
    """
    # Arrange
    history, expected_win_rate = win_rate_scenario
    
    mock_session = mocker.AsyncMock()
    # We mock the repository's method to avoid creating a real repo instance
    mock_repo_instance = mocker.AsyncMock()
    mock_repo_instance.get_player_hero_win_history.return_value = history
    
    # We patch the HistoryRepository class to return our mock instance when instantiated
    mocker.patch(
        f'{FUNCTION_FP}.HistoryRepository',
        return_value=mock_repo_instance
    )
    
    # Act
    win_rate = await player_hero_features_creator._calculate_win_rate(
        session=mock_session,
        account_id=1,
        hero_id=2,
        before=datetime.now(timezone.utc)
    )
    
    # Assert
    assert win_rate == pytest.approx(expected_win_rate)
    mock_repo_instance.get_player_hero_win_history.assert_awaited_once_with(
        1, 2, ANY
    )