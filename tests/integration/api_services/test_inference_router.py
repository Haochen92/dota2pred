"""
Unit tests for the Inference Router.
"""

from unittest.mock import patch


def test_predict_success(inference_client, mock_http_client):
    """Test successful prediction request."""
    # ARRANGE
    request_data = {"feature1": 1.0, "feature2": 2.0}
    expected_response = {"prediction": 0.85, "confidence": 0.92}

    # Configure mock response
    mock_response = mock_http_client.return_value.__aenter__.return_value.post.return_value
    mock_response.json.return_value = expected_response

    # Mock httpx.AsyncClient to return our mock
    with patch("httpx.AsyncClient", return_value=mock_http_client):
        # ACT
        response = inference_client.post("/matchtable/predict", json=request_data)

        # ASSERT
        assert response.status_code == 200
        data = response.json()
        assert data == expected_response


def test_predict_external_service_error(inference_client, mock_http_client):
    """Test handling of external service errors."""
    # ARRANGE
    request_data = {"feature1": 1.0, "feature2": 2.0}

    # Configure mock to raise exception
    mock_http_client.return_value.__aenter__.return_value.post.side_effect = Exception("Connection failed")

    with patch("httpx.AsyncClient", return_value=mock_http_client):
        # ACT & ASSERT
        response = inference_client.post("/matchtable/predict", json=request_data)
        assert response.status_code == 500


def test_predict_invalid_json(inference_client):
    """Test handling of invalid JSON data."""
    # ACT & ASSERT
    response = inference_client.post("/matchtable/predict", data="invalid json")
    assert response.status_code == 422  # Unprocessable Entity


def test_inference_router_configuration(inference_router):
    """Test router configuration."""
    assert inference_router.prefix == "/matchtable"
    assert "matchtable" in inference_router.tags

    # Check that the route exists
    routes = [route.path for route in inference_router.routes]
    assert "/matchtable/predict" in routes
