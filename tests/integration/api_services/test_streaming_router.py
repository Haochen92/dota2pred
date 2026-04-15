"""
Unit tests for the Streaming Router.
"""


def test_post_live_state_update_success(api_layer_client, mock_redis_pubsub_service, live_state_update_request_factory):
    """Test successful live state update posting."""
    # ARRANGE
    update_request = live_state_update_request_factory.build()

    # ACT
    response = api_layer_client.post("/streaming/live-state-update", json=update_request.model_dump(mode="json"))

    # ASSERT
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "success"
    mock_redis_pubsub_service.publish_live_update.assert_awaited_once()


def test_post_live_state_update_invalid_data(api_layer_client):
    """Test handling of invalid live state update data."""
    # ARRANGE
    invalid_data = {"invalid": "data"}

    # ACT & ASSERT
    response = api_layer_client.post("/streaming/live-state-update", json=invalid_data)
    assert response.status_code == 422  # Unprocessable Entity


def test_post_live_state_update_pubsub_error(
    api_layer_client, mock_redis_pubsub_service, live_state_update_request_factory
):
    """Test handling of pubsub service errors."""
    # ARRANGE
    update_request = live_state_update_request_factory.build()
    mock_redis_pubsub_service.publish_live_update.side_effect = Exception("Redis error")

    # ACT & ASSERT
    response = api_layer_client.post("/streaming/live-state-update", json=update_request.model_dump(mode="json"))
    assert response.status_code == 500


def test_get_live_state_sse_endpoint_exists(api_layer_client):
    """Test that SSE endpoint is registered on the test app."""
    routes = {route.path for route in api_layer_client.app.routes if hasattr(route, "path")}
    assert "/streaming/sse/live_matches" in routes


def test_streaming_router_configuration(streaming_router):
    """Test router configuration."""
    assert streaming_router.prefix == "/streaming"
    assert "streaming" in streaming_router.tags

    # Check that the routes exist
    routes = [route.path for route in streaming_router.routes]
    assert "/streaming/live-state-update" in routes
    assert "/streaming/sse/live_matches" in routes
