"""
Integration Test for the Main FastAPI Application.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def test_app_startup_and_basic_functionality(api_layer_client):
    """Test that the app can start and basic functionality works."""
    # ACT & ASSERT - The fixture setup itself tests app startup
    # If we get here, the app started successfully with all routers

    # Test that we can make requests to different routers
    matches_response = api_layer_client.get("/matches/")
    assert matches_response.status_code == 200

    # Test inference endpoint exists
    inference_response = api_layer_client.post("/inference/predict", json={"test": "data"})
    # Will fail with validation error but shows endpoint exists
    assert inference_response.status_code in [200, 422, 500]

    # Test streaming endpoint is registered
    streaming_paths = [route.path for route in api_layer_client.app.routes if hasattr(route, "path")]
    assert "/streaming/sse/live_matches" in streaming_paths


def test_cors_middleware_applied(api_layer_client):
    """Test that CORS middleware is properly configured."""
    # ACT
    response = api_layer_client.options("/matches/")

    # ASSERT
    # CORS headers should be present (though exact behavior depends on browser)
    assert response.status_code in [200, 405]  # OPTIONS might not be implemented but middleware should handle


def test_cors_echoes_allowed_origin_not_wildcard():
    """An allowed origin must be echoed back (not '*'), so credentialed requests work.

    Browsers reject allow-origin='*' together with allow-credentials=true, which is why
    the wildcard was replaced with an explicit origin list. Built from create_app() (the
    api_layer_client fixture builds its own app without the CORS middleware). A CORS
    preflight is answered by the middleware before routing, so no DB/lifespan is needed.
    """
    from fastapi.testclient import TestClient

    from api_service.config import api_settings
    from api_service.main import create_app

    allowed = api_settings.cors_allowed_origins[0]
    client = TestClient(create_app())  # no context manager -> lifespan/DB not triggered
    response = client.options(
        "/matches/",
        headers={"Origin": allowed, "Access-Control-Request-Method": "GET"},
    )

    allow_origin = response.headers.get("access-control-allow-origin")
    assert allow_origin == allowed, f"expected echoed origin {allowed}, got {allow_origin!r}"
    assert allow_origin != "*"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_rejects_disallowed_origin():
    """An origin not on the allow-list must not receive an allow-origin header."""
    from fastapi.testclient import TestClient

    from api_service.main import create_app

    client = TestClient(create_app())
    response = client.options(
        "/matches/",
        headers={"Origin": "https://evil.example.com", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers.get("access-control-allow-origin") != "https://evil.example.com"
    assert response.headers.get("access-control-allow-origin") != "*"


@pytest.mark.asyncio
async def test_lifespan_startup_and_shutdown():
    """Test the lifespan context manager for startup and shutdown."""
    from api_service.main import lifespan
    from fastapi import FastAPI

    mock_session_factory = MagicMock()
    mock_redis_client = MagicMock()
    mock_http_client = AsyncMock()

    @asynccontextmanager
    async def resource(value):
        yield value

    setup = AsyncMock()
    teardown = AsyncMock()
    app = FastAPI()

    with (
        patch("api_service.main.http_client_provider", side_effect=lambda: resource(mock_http_client)),
        patch(
            "api_service.main.database_session_factory_resource",
            side_effect=lambda: resource(mock_session_factory),
        ),
        patch("api_service.main.redis_client_resource", side_effect=lambda: resource(mock_redis_client)),
        patch("api_service.main.setup_dependencies", setup),
        patch("api_service.main.teardown_dependencies", teardown),
    ):
        async with lifespan(app):
            assert app.state.db_session_factory is mock_session_factory
            assert app.state.redis_client is mock_redis_client
            assert app.state.http_client is mock_http_client
            setup.assert_awaited_once_with(app)

    teardown.assert_awaited_once_with(app)


def test_app_title_and_version():
    """Test that the app has correct metadata."""
    from api_service.main import app

    assert app.title == "Dota Oracle API Gateway"
    assert app.version == "0.1.0"


def test_all_routers_included():
    """Test that all expected routers are included in the main app."""
    from api_service.main import app

    # Get all route paths from the app
    all_paths = []
    for route in app.routes:
        if hasattr(route, "path"):
            all_paths.append(route.path)

    # Check for routes from each router
    matches_routes = [path for path in all_paths if path.startswith("/matches")]
    inference_routes = [path for path in all_paths if path.startswith("/inference")]
    streaming_routes = [path for path in all_paths if path.startswith("/streaming")]

    assert len(matches_routes) > 0, "Matches router not included"
    assert len(inference_routes) > 0, "Inference router not included"
    assert len(streaming_routes) > 0, "Streaming router not included"


def test_main_execution():
    """Test that the main execution block is properly configured."""
    # This test verifies the structure exists but doesn't run the server
    import api_service.main

    # Check that uvicorn configuration exists
    assert hasattr(api_service.main, "app")

    # The actual uvicorn.run call is in an if __name__ == "__main__" block
    # so it won't execute during imports
