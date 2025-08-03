import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock


# Path to the service being tested
F_PATH = "live_orchestrator_app.services.feature_preparation_service"


# --- Tests for prepare_features_for_inference (Public Method) ---


@pytest.mark.asyncio
async def test_prepare_features_for_inference_happy_path(
    feature_preparation_service,
    mock_async_session,
    mocker,
    team_features_table_factory,
    hero_features_table_factory,
    player_hero_feature_table_factory,
):
    """
    Tests the full, successful pipeline. This version simplifies mocking to avoid integration issues.
    """
    # ARRANGE
    match_id = 123
    expected_feature_names = ["f1", "f2", "f3", "rh_1", "dh_2"]
    feature_preparation_service.model_feature_names = expected_feature_names

    # Mock the internal helper methods directly to isolate the orchestration logic.
    mocker.patch(f"{F_PATH}.MatchRepository")
    mocker.patch(f"{F_PATH}.HeroesRepository")

    # 1. Mock the DB fetch result
    mock_db_result = (
        team_features_table_factory.build(),
        hero_features_table_factory.build(),
        player_hero_feature_table_factory.build(),
    )
    mocker.patch.object(feature_preparation_service, "_get_features_from_db", return_value=mock_db_result)

    # 2. Mock the encoding result
    mocker.patch.object(
        feature_preparation_service, "_encode_hero_feature", return_value=pd.DataFrame([{"match_id": match_id}])
    )

    # 3. Mock the final merge result
    final_df = pd.DataFrame([[10, 20, 30, 1, 2]], columns=expected_feature_names)
    mocker.patch.object(feature_preparation_service, "_merge_and_filter_dataframe", return_value=final_df)

    # ACT
    result_array = await feature_preparation_service.prepare_features_for_inference(match_id, mock_async_session)

    # ASSERT
    assert isinstance(result_array, np.ndarray)
    expected_list = [10, 20, 30, 1, 2]
    assert result_array.tolist()[0] == expected_list

    feature_preparation_service._get_features_from_db.assert_awaited_once()
    feature_preparation_service._encode_hero_feature.assert_awaited_once()
    feature_preparation_service._merge_and_filter_dataframe.assert_called_once()


# --- Unit Tests for Private Helper Methods ---


@pytest.mark.asyncio
async def test_get_features_from_db_success(
    feature_preparation_service,
    mock_match_repository,  # From your conftest
    team_features_table_factory,
    hero_features_table_factory,
    player_hero_feature_table_factory,
):
    """Tests that features are correctly extracted from a full match instance."""
    # ARRANGE
    match_id = 123
    mock_team = team_features_table_factory.build(match_id=match_id)
    mock_hero = hero_features_table_factory.build(match_id=match_id)
    mock_player = player_hero_feature_table_factory.build(match_id=match_id)

    mock_match_instance = MagicMock(team_features=mock_team, hero_features=mock_hero, player_hero_features=mock_player)
    mock_match_repository.get_match_details.return_value = [mock_match_instance]

    # ACT
    res = await feature_preparation_service._get_features_from_db(match_id, mock_match_repository)

    # ASSERT
    assert res == (mock_team, mock_hero, mock_player)
    mock_match_repository.get_match_details.assert_awaited_once_with(
        input_id_list=[match_id],
        relationship_fields=["team_features", "player_hero_features", "hero_features"],
        limit=1,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("missing_feature", ["team_features", "hero_features", "player_hero_features"])
async def test_get_features_from_db_incomplete_data(
    feature_preparation_service,
    mock_match_repository,  # From your conftest
    missing_feature,
    team_features_table_factory,
    hero_features_table_factory,
    player_hero_feature_table_factory,
):
    """Tests that None is returned if any of the required feature tables are missing."""
    # ARRANGE
    match_id = 123
    mock_match_instance = MagicMock(
        team_features=team_features_table_factory.build(match_id=match_id),
        hero_features=hero_features_table_factory.build(match_id=match_id),
        player_hero_features=player_hero_feature_table_factory.build(match_id=match_id),
    )
    # Set one of the required features to None
    setattr(mock_match_instance, missing_feature, None)

    mock_match_repository.get_match_details.return_value = [mock_match_instance]

    # ACT
    res = await feature_preparation_service._get_features_from_db(match_id, mock_match_repository)

    # ASSERT
    assert res is None


@pytest.mark.asyncio
async def test_encode_hero_feature_success(feature_preparation_service, mock_heroes_repository, mocker):
    """Tests successful encoding of hero features."""
    # ARRANGE
    mock_hero_map = {1: "npc_dota_hero_antimage"}
    mock_heroes_repository.get_hero_id_map.return_value = mock_hero_map

    input_df = pd.DataFrame([{"radiant_hero_id_1": 1}])
    encoded_df = pd.DataFrame([{"radiant_hero_id_1_encoded": 1}])

    mock_encoder = mocker.patch(f"{F_PATH}.FeatureEncoder.encode_hero_features", return_value=encoded_df)

    # ACT
    result_df = await feature_preparation_service._encode_hero_feature(mock_heroes_repository, input_df)

    # ASSERT
    assert result_df is encoded_df
    mock_heroes_repository.get_hero_id_map.assert_awaited_once()
    mock_encoder.assert_called_once_with(input_df, mock_hero_map)


def test_merge_and_filter_dataframe_success(feature_preparation_service):
    """Tests the core logic of merging and filtering dataframes."""
    # ARRANGE
    # Explicitly set the feature names the model expects for this test
    feature_preparation_service.model_feature_names = ["f1", "f3", "radiant_hero_id_1"]

    hero_df = pd.DataFrame([{"match_id": 123, "radiant_hero_id_1": 1, "dire_hero_id_5": 5}])
    team_df = pd.DataFrame([{"match_id": 123, "f1": 10, "f_extra": 99}])
    player_hero_df = pd.DataFrame([{"match_id": 123, "f3": 30}])

    # ACT
    final_df = feature_preparation_service._merge_and_filter_dataframe(hero_df, team_df, player_hero_df)

    # ASSERT
    assert not final_df.empty
    assert final_df.shape == (1, 3)
    # Check that only the required columns are present, in the correct order
    assert final_df.columns.to_list() == ["f1", "f3", "radiant_hero_id_1"]
    assert final_df.iloc[0]["f1"] == 10
    assert final_df.iloc[0]["f3"] == 30
    assert final_df.iloc[0]["radiant_hero_id_1"] == 1


def test_merge_and_filter_dataframe_missing_required_column(feature_preparation_service):
    """Tests that None is returned if a required feature column is missing after merge."""
    # ARRANGE
    feature_preparation_service.model_feature_names = ["f1", "f_missing"]  # Expects a missing column

    hero_df = pd.DataFrame([{"match_id": 123}])
    team_df = pd.DataFrame([{"match_id": 123, "f1": 10}])
    player_hero_df = pd.DataFrame([{"match_id": 123}])

    # ACT
    final_df = feature_preparation_service._merge_and_filter_dataframe(hero_df, team_df, player_hero_df)

    # ASSERT
    assert final_df is None
