"""
Unit tests for the Inference Router.
"""


def test_predict_success(api_layer_client):
    """Test successful prediction request."""
    # ARRANGE
    request_data = {"feature1": 1.0, "feature2": 2.0}

    # ACT - The mock_prediction_service_api fixture should automatically handle the external call
    response = api_layer_client.post("/inference/predict", json=request_data)

    # ASSERT
    assert response.status_code == 200
    data = response.json()
    assert data == {"prediction": "mocked_success"}  # This matches your api_mocks.py


def test_predict_external_service_error(api_layer_client, respx_mock):
    """Test handling of external service errors."""
    # ARRANGE
    request_data = {"feature1": 1.0, "feature2": 2.0}

    # Override the default mock to simulate an error
    from dota_oracle_common.constants.endpoint_configs import service_url
    import httpx

    respx_mock.post(service_url.PUBLIC_MATCHES_INFERENCE_URL).mock(
        return_value=httpx.Response(500, json={"error": "Service unavailable"})
    )

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
