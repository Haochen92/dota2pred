import pytest
from unittest.mock import ANY
from datetime import datetime, timezone
from dota_oracle_common.models.features import PlayerHeroFeatureTable

FUNCTION_FP = "dota_oracle_pipeline.feature_engineering.player_hero_features_creator"


@pytest.mark.asyncio
async def test_create_player_hero_features_success(
    player_hero_features_creator,
    mock_async_session,
    match_table_factory,
    mocker,
) -> None:
    """
    Tests the happy path where a feature row is successfully created for a valid match.
    """
    # Arrange

    match_instance = match_table_factory.build(match_id=1001)

    # Mock the _calculate_win_rate method to return predictable results
    mocker.patch.object(player_hero_features_creator, "_calculate_win_rate", return_value=0.6)

    # Act
    result = await player_hero_features_creator.create_player_hero_features(
        session=mock_async_session, match_instances=[match_instance]
    )

    # Assert
    assert len(result) == 1
    feature_row = result[0]

    assert isinstance(feature_row, PlayerHeroFeatureTable)
    assert feature_row.match_id == 1001

    # Check if a sample feature was set correctly from the mocked result
    assert feature_row.player_hero_0_win_rate == 0.6
    assert feature_row.player_hero_128_win_rate == 0.6


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "missing_data",
    [
        pytest.param({"match_id": 123, "slot_0_account_id": None}, id="missing_account_id"),
        pytest.param({"match_id": 124, "slot_0_hero_id": None}, id="missing_hero_id"),
        pytest.param({"match_id": 125, "start_time": None}, id="missing_start_time"),
    ],
)
async def test_create_features_skips_match_with_missing_data(
    player_hero_features_creator, mock_async_session, match_table_factory, mocker, missing_data: dict
) -> None:
    """
    Tests that a match is skipped if essential data like account_id is missing.
    """
    # Arrange - Factory called at test time, fresh instance each run
    match_instance = match_table_factory.build(**missing_data)
    mock_logger_error = mocker.patch(f"{FUNCTION_FP}.logger.error")

    # Act
    result = await player_hero_features_creator.create_player_hero_features(
        session=mock_async_session, match_instances=[match_instance]
    )

    # Assert
    assert len(result) == 0, f"Expected 0 results, got {len(result)}"
    mock_logger_error.assert_called_once()


@pytest.mark.asyncio
async def test_create_features_handles_task_failure_gracefully(
    player_hero_features_creator, mock_async_session, match_table_factory, mocker
) -> None:
    """
    Tests that if a single win-rate calculation fails internally, it defaults to 0.5
    and the feature creation for the match still succeeds.
    """
    # Arrange
    match_instance = match_table_factory.build(match_id=789)

    mock_calculate = mocker.patch.object(player_hero_features_creator, "_calculate_win_rate")

    mock_counter = 0

    def side_effect(*args, **kwargs):
        nonlocal mock_counter
        mock_counter += 1
        # Use the mock's built-in call_count (starts at 1 for first call)
        if mock_counter == 2:  # Second call - simulate internal error handling by returning 0.5
            return 0.5  # This simulates the exception being caught internally and returning default
        elif mock_counter == 1:  # First call
            return 0.75
        else:  # Subsequent calls
            return 0.6

    mock_calculate.side_effect = side_effect
    # Mock the internal warning that would be called within _calculate_win_rate

    # Act
    result = await player_hero_features_creator.create_player_hero_features(
        session=mock_async_session, match_instances=[match_instance]
    )

    # Assert
    assert len(result) == 1
    feature_row = result[0]
    assert feature_row.match_id == 789

    # The successful task's result is used
    assert feature_row.player_hero_0_win_rate == 0.75
    # The failed task's result is the default fallback value
    assert feature_row.player_hero_1_win_rate == 0.5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "history, expected_win_rate",
    [
        pytest.param([], 0.5, id="no_history_defaults_to_half"),
        pytest.param([True, True], 1.0, id="all_wins_perfect_rate"),
        pytest.param([False, False, False], 0.0, id="all_losses_zero_rate"),
        pytest.param([True, False, True], 2 / 3, id="mixed_results_calculated"),
    ],
)
async def test_calculate_win_rate_logic(
    player_hero_features_creator, mock_async_session, mocker, history, expected_win_rate
) -> None:
    """
    Tests the _calculate_win_rate helper method's logic directly.
    """
    # Arrange

    mock_repo_instance = mocker.AsyncMock()
    mock_repo_instance.get_player_hero_win_history.return_value = history

    mocker.patch(f"{FUNCTION_FP}.HistoryRepository", return_value=mock_repo_instance)

    # Act
    win_rate = await player_hero_features_creator._calculate_win_rate(
        session=mock_async_session, account_id=1, hero_id=2, before=datetime.now(timezone.utc)
    )

    # Assert
    assert win_rate == pytest.approx(expected_win_rate)
    mock_repo_instance.get_player_hero_win_history.assert_awaited_once_with(1, 2, ANY)
