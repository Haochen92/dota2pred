"""
Unit tests for the Inference Router.
"""


def test_predict_success(api_layer_client, mock_public_inference_service):
    """Test successful prediction request."""
    # ARRANGE
    request_data = {
        "radiant_heroes": [1, 2, 3, 4, 5],
        "dire_heroes": [6, 7, 8, 9, 10],
    }
    from dota_oracle_common.models.api import PublicMatchPredictionResponse

    mock_public_inference_service.run_inference_cycle.return_value = PublicMatchPredictionResponse(
        prediction=True, probability=0.72
    )

    # ACT - The mock_prediction_service_api fixture should automatically handle the external call
    response = api_layer_client.post("/inference/predict", json=request_data)

    # ASSERT
    assert response.status_code == 200
    data = response.json()
    assert data["prediction"] is True
    assert data["probability"] == 0.72


def test_predict_external_service_error(api_layer_client, mock_public_inference_service):
    """Test handling of external service errors."""
    # ARRANGE
    request_data = {
        "radiant_heroes": [1, 2, 3, 4, 5],
        "dire_heroes": [6, 7, 8, 9, 10],
    }

    # Make the service raise to simulate downstream failure
    mock_public_inference_service.run_inference_cycle.side_effect = Exception("Service unavailable")

    # ACT
    response = api_layer_client.post("/inference/predict", json=request_data)

    # ASSERT
    # The router should return whatever the external service returns
    assert response.status_code == 500


def test_predict_invalid_json(api_layer_client):
    """Test handling of invalid JSON data."""
    # ACT & ASSERT
    response = api_layer_client.post("/inference/predict", data="invalid json")
    assert response.status_code == 422  # Unprocessable Entity


def test_inference_router_configuration(inference_router):
    """Test router configuration."""
    assert inference_router.prefix == "/inference"
    assert "inference" in inference_router.tags

    # Check that the route exists
    routes = [route.path for route in inference_router.routes]
    assert "/inference/predict" in routes
