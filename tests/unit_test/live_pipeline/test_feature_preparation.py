import numpy as np
import pytest


F_PATH = "live_orchestrator_app.services.feature_preparation_service"


@pytest.mark.asyncio
async def test_prepare_features_for_inference_happy_path(
    unit_test_feature_preparation_service,
    mocker,
    prediction_payload_factory,
):
    unit_test_feature_preparation_service.model_feature_names = ["f1", "f2", "f3"]
    prediction_payload = prediction_payload_factory.build()

    final_feature = mocker.Mock()
    final_feature.model_dump.return_value = {"f1": 10, "f2": 20, "f3": 30}
    mock_create_final_features = mocker.patch(f"{F_PATH}.create_final_features", return_value=[final_feature])

    result = await unit_test_feature_preparation_service.prepare_features_for_inference(prediction_payload)

    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.shape == (1, 3)
    np.testing.assert_array_equal(result, np.array([[10, 20, 30]]))
    mock_create_final_features.assert_called_once()


@pytest.mark.asyncio
async def test_prepare_features_for_inference_returns_none_when_feature_set_missing(
    unit_test_feature_preparation_service,
    prediction_payload_factory,
):
    prediction_payload = prediction_payload_factory.build()
    prediction_payload.team_features = None

    result = await unit_test_feature_preparation_service.prepare_features_for_inference(prediction_payload)

    assert result is None


@pytest.mark.asyncio
async def test_prepare_features_for_inference_returns_none_when_final_features_are_empty(
    unit_test_feature_preparation_service,
    mocker,
    prediction_payload_factory,
):
    prediction_payload = prediction_payload_factory.build()
    mocker.patch(f"{F_PATH}.create_final_features", return_value=[])

    result = await unit_test_feature_preparation_service.prepare_features_for_inference(prediction_payload)

    assert result is None


@pytest.mark.asyncio
async def test_prepare_features_for_inference_raises_when_required_columns_are_missing(
    unit_test_feature_preparation_service,
    mocker,
    prediction_payload_factory,
):
    unit_test_feature_preparation_service.model_feature_names = ["required_feature"]
    prediction_payload = prediction_payload_factory.build()

    final_feature = mocker.Mock()
    final_feature.model_dump.return_value = {"different_feature": 10}
    mocker.patch(f"{F_PATH}.create_final_features", return_value=[final_feature])

    with pytest.raises(ValueError, match="Missing required feature columns"):
        await unit_test_feature_preparation_service.prepare_features_for_inference(prediction_payload)
