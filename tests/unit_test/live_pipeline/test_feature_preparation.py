import pytest
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock


# Path to the service being tested
F_PATH = "live_orchestrator_app.services.feature_preparation_service"


# --- Tests for prepare_features_for_inference (Public Method) ---


@pytest.mark.asyncio
async def test_prepare_features_for_inference_happy_path(
    unit_test_feature_preparation_service,
    mock_async_session,
    mocker,
    prediction_payload_factory,
):
    """
    Tests the full, successful pipeline with the new PredictionPayload-based approach.
    """
    # ARRANGE
    expected_feature_names = ["f1", "f2", "f3", "rh_1", "dh_2"]
    unit_test_feature_preparation_service.model_feature_names = expected_feature_names

    # Create a prediction payload with the required features
    prediction_payload = prediction_payload_factory.build()

    # Mock the internal helper methods directly to isolate the orchestration logic.
    mocker.patch(f"{F_PATH}.HeroesRepository")

    # Mock the encoding result
    encoded_hero_df = pd.DataFrame([[123, 1, 2]], columns=["match_id", "rh_1", "dh_2"])
    mocker.patch.object(unit_test_feature_preparation_service, "_encode_hero_feature", return_value=encoded_hero_df)

    # Mock the final merge result
    final_df = pd.DataFrame([[10, 20, 30, 1, 2]], columns=expected_feature_names)
    mocker.patch.object(unit_test_feature_preparation_service, "_merge_and_filter_dataframe", return_value=final_df)

    # ACT
    result = await unit_test_feature_preparation_service.prepare_features_for_inference(
        prediction_payload, mock_async_session
    )

    # ASSERT
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.shape == (1, 5)
    np.testing.assert_array_equal(result, np.array([[10, 20, 30, 1, 2]]))


@pytest.mark.asyncio
async def test_prepare_features_for_inference_encoding_returns_none(
    unit_test_feature_preparation_service,
    mock_async_session,
    mocker,
    prediction_payload_factory,
):
    """Tests when hero encoding returns None."""
    # ARRANGE
    prediction_payload = prediction_payload_factory.build()

    mocker.patch(f"{F_PATH}.HeroesRepository")
    mocker.patch.object(unit_test_feature_preparation_service, "_encode_hero_feature", return_value=None)

    # ACT
    result = await unit_test_feature_preparation_service.prepare_features_for_inference(
        prediction_payload, mock_async_session
    )

    # ASSERT
    assert result is None


@pytest.mark.asyncio
async def test_prepare_features_for_inference_encoding_returns_empty(
    unit_test_feature_preparation_service,
    mock_async_session,
    mocker,
    prediction_payload_factory,
):
    """Tests when hero encoding returns empty DataFrame."""
    # ARRANGE
    prediction_payload = prediction_payload_factory.build()

    mocker.patch(f"{F_PATH}.HeroesRepository")
    mocker.patch.object(unit_test_feature_preparation_service, "_encode_hero_feature", return_value=pd.DataFrame())

    # ACT
    result = await unit_test_feature_preparation_service.prepare_features_for_inference(
        prediction_payload, mock_async_session
    )

    # ASSERT
    assert result is None


@pytest.mark.asyncio
async def test_prepare_features_for_inference_merge_returns_none(
    unit_test_feature_preparation_service,
    mock_async_session,
    mocker,
    prediction_payload_factory,
):
    """Tests when feature merging returns None."""
    # ARRANGE
    prediction_payload = prediction_payload_factory.build()

    mocker.patch(f"{F_PATH}.HeroesRepository")
    encoded_hero_df = pd.DataFrame([[123, 1, 2]], columns=["match_id", "rh_1", "dh_2"])
    mocker.patch.object(unit_test_feature_preparation_service, "_encode_hero_feature", return_value=encoded_hero_df)
    mocker.patch.object(unit_test_feature_preparation_service, "_merge_and_filter_dataframe", return_value=None)

    # ACT
    result = await unit_test_feature_preparation_service.prepare_features_for_inference(
        prediction_payload, mock_async_session
    )

    # ASSERT
    assert result is None


# --- Tests for _encode_hero_feature (Private Method) ---


@pytest.mark.asyncio
async def test_encode_hero_feature_success(unit_test_feature_preparation_service, mocker):
    """Tests successful hero feature encoding."""
    # ARRANGE
    mock_heroes_repository = AsyncMock()
    hero_map = {"hero_1": 1, "hero_2": 2}
    mock_heroes_repository.get_hero_id_map.return_value = hero_map

    input_df = pd.DataFrame([{"match_id": 123, "radiant_hero_1": "hero_1", "dire_hero_1": "hero_2"}])
    expected_df = pd.DataFrame([{"match_id": 123, "rh_1": 1, "dh_1": 2}])

    # Mock FeatureEncoder.encode_hero_features
    mocker.patch(f"{F_PATH}.FeatureEncoder.encode_hero_features", return_value=expected_df)

    # ACT
    result = await unit_test_feature_preparation_service._encode_hero_feature(mock_heroes_repository, input_df)

    # ASSERT
    assert result is not None
    pd.testing.assert_frame_equal(result, expected_df)
    mock_heroes_repository.get_hero_id_map.assert_awaited_once()


@pytest.mark.asyncio
async def test_encode_hero_feature_no_hero_map(unit_test_feature_preparation_service):
    """Tests when hero map is missing."""
    # ARRANGE
    mock_heroes_repository = AsyncMock()
    mock_heroes_repository.get_hero_id_map.return_value = None
    input_df = pd.DataFrame([{"match_id": 123}])

    # ACT
    result = await unit_test_feature_preparation_service._encode_hero_feature(mock_heroes_repository, input_df)

    # ASSERT
    assert result is None


@pytest.mark.asyncio
async def test_encode_hero_feature_empty_hero_map(unit_test_feature_preparation_service):
    """Tests when hero map is empty."""
    # ARRANGE
    mock_heroes_repository = AsyncMock()
    mock_heroes_repository.get_hero_id_map.return_value = {}
    input_df = pd.DataFrame([{"match_id": 123}])

    # ACT
    result = await unit_test_feature_preparation_service._encode_hero_feature(mock_heroes_repository, input_df)

    # ASSERT
    assert result is None


# --- Tests for _merge_and_filter_dataframe (Private Method) ---


def test_merge_and_filter_dataframe_success(unit_test_feature_preparation_service):
    """Tests successful merging and filtering of dataframes."""
    # ARRANGE
    unit_test_feature_preparation_service.model_feature_names = ["f1", "f2", "f3"]

    hero_df = pd.DataFrame([{"match_id": 123, "f1": 10}])
    team_df = pd.DataFrame([{"match_id": 123, "f2": 20}])
    player_hero_df = pd.DataFrame([{"match_id": 123, "f3": 30}])

    # ACT
    result = unit_test_feature_preparation_service._merge_and_filter_dataframe(
        hero_features=hero_df, team_features=team_df, player_hero_features=player_hero_df
    )

    # ASSERT
    assert result is not None
    assert list(result.columns) == ["f1", "f2", "f3"]
    assert result.iloc[0]["f1"] == 10
    assert result.iloc[0]["f2"] == 20
    assert result.iloc[0]["f3"] == 30


def test_merge_and_filter_dataframe_missing_match_id(unit_test_feature_preparation_service):
    """Tests when match_id is missing from one of the dataframes."""
    # ARRANGE
    hero_df = pd.DataFrame([{"f1": 10}])  # Missing match_id
    team_df = pd.DataFrame([{"match_id": 123, "f2": 20}])
    player_hero_df = pd.DataFrame([{"match_id": 123, "f3": 30}])

    # ACT
    result = unit_test_feature_preparation_service._merge_and_filter_dataframe(
        hero_features=hero_df, team_features=team_df, player_hero_features=player_hero_df
    )

    # ASSERT
    assert result is None


def test_merge_and_filter_dataframe_missing_required_column(unit_test_feature_preparation_service):
    """Tests when required feature columns are missing."""
    # ARRANGE
    unit_test_feature_preparation_service.model_feature_names = ["f1", "f2", "f3", "missing_col"]

    hero_df = pd.DataFrame([{"match_id": 123, "f1": 10}])
    team_df = pd.DataFrame([{"match_id": 123, "f2": 20}])
    player_hero_df = pd.DataFrame([{"match_id": 123, "f3": 30}])

    # ACT
    result = unit_test_feature_preparation_service._merge_and_filter_dataframe(
        hero_features=hero_df, team_features=team_df, player_hero_features=player_hero_df
    )

    # ASSERT
    assert result is None


def test_merge_and_filter_dataframe_empty_after_merge(unit_test_feature_preparation_service):
    """Tests when merge results in empty dataframe."""
    # ARRANGE
    unit_test_feature_preparation_service.model_feature_names = ["f1", "f2", "f3"]

    hero_df = pd.DataFrame([{"match_id": 123, "f1": 10}])
    team_df = pd.DataFrame([{"match_id": 456, "f2": 20}])  # Different match_id
    player_hero_df = pd.DataFrame([{"match_id": 123, "f3": 30}])

    # ACT
    result = unit_test_feature_preparation_service._merge_and_filter_dataframe(
        hero_features=hero_df, team_features=team_df, player_hero_features=player_hero_df
    )

    # ASSERT
    assert result is None
