"""
Unit tests for the Streaming Router.
"""


def test_post_live_state_update_success(streaming_client, mock_redis_pubsub_service, live_state_update_request_factory):
    """Test successful live state update posting."""
    # ARRANGE
    update_request = live_state_update_request_factory.build()

    # ACT
    response = streaming_client.post("/streaming/live-state-update", json=update_request.model_dump())

    # ASSERT
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "success"
    mock_redis_pubsub_service.publish_live_update.assert_awaited_once()


def test_post_live_state_update_invalid_data(streaming_client):
    """Test handling of invalid live state update data."""
    # ARRANGE
    invalid_data = {"invalid": "data"}

    # ACT & ASSERT
    response = streaming_client.post("/streaming/live-state-update", json=invalid_data)
    assert response.status_code == 422  # Unprocessable Entity


def test_post_live_state_update_pubsub_error(
    streaming_client, mock_redis_pubsub_service, live_state_update_request_factory
):
    """Test handling of pubsub service errors."""
    # ARRANGE
    update_request = live_state_update_request_factory.build()
    mock_redis_pubsub_service.publish_live_update.side_effect = Exception("Redis error")

    # ACT & ASSERT
    response = streaming_client.post("/streaming/live-state-update", json=update_request.model_dump())
    assert response.status_code == 500


def test_get_live_state_sse_endpoint_exists(streaming_client):
    """Test that SSE endpoint exists and responds appropriately."""
    # ACT
    response = streaming_client.get("/streaming/sse/live_matches")

    # ASSERT
    # SSE endpoints typically return 200 and stream data
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")


def test_streaming_router_configuration(streaming_router):
    """Test router configuration."""
    assert streaming_router.prefix == "/streaming"
    assert "streaming" in streaming_router.tags

    # Check that the routes exist
    routes = [route.path for route in streaming_router.routes]
    assert "/streaming/live-state-update" in routes
    assert "/streaming/sse/live_matches" in routes
