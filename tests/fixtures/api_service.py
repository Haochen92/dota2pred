"""
API Service-related fixtures for tests.

This file provides a clear hierarchy of fixtures based on the type of test being run:

1.  UNIT TESTS (Business Logic):
    - Use 'unit_test_*' service fixtures directly to test a service's internal logic.
    - These fixtures are the "Subjects Under Test" (SUTs) and have their own
      low-level dependencies (like a raw Redis client) mocked.
    - Example: def test_retry_logic(unit_test_redis_pubsub_service): ...

2.  API LAYER TESTS (Fast, Isolated Integration):
    - Use the 'api_layer_client' fixture.
    - This tests the FastAPI layer (routing, validation, serialization) with ALL
      underlying business logic and services completely mocked using high-level mocks.
    - This is THE DEFAULT CLIENT for most API endpoint tests.
    - Example: def test_get_matches_bad_request(api_layer_client): ...

3.  FULL STACK TESTS (Slow, End-to-End Integration):
    - Use the 'full_stack_client' fixture.
    - This tests the entire application stack from an HTTP request down to a REAL
      test database and a REAL test Redis container.
    - Use these sparingly for critical, end-to-end user flows.
    - Example: def test_e2e_live_update_and_db_read(full_stack_client): ...
"""

import asyncio
from typing import Callable
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI, APIRouter
from unittest.mock import create_autospec, MagicMock
import pytest_asyncio

# Import actual services and dependency functions for speccing and type-safe overrides
from api_service.dependencies import (
    get_match_pagination_service,
    get_pubsub_service,
    get_http_client,
    get_public_inference_service,
)
from api_service.matches.match_pagination_service import MatchPaginationService
from api_service.streaming.redis_pubsub_service import RedisPubSubService
from api_service.inference.pub_inference import PubInferenceService
from api_service.inference.model_history_service import ModelHistoryService
import httpx

# Import dependent services


# =================================================================================
# LEVEL 1: FIXTURES FOR UNIT TESTING (Business Logic)
# =================================================================================

# --- High-Level Mocks (Used as dependencies for API Layer tests) ---


@pytest.fixture
def mock_match_pagination_service() -> MatchPaginationService:
    """Provides a high-fidelity mock of the entire MatchPaginationService."""
    return create_autospec(MatchPaginationService, instance=True)


@pytest.fixture
def mock_redis_pubsub_service() -> RedisPubSubService:
    """Provides a high-fidelity mock of the entire RedisPubSubService."""
    mock = create_autospec(RedisPubSubService, instance=True)
    mock.get_cached_snapshot.return_value = None
    mock.cache_snapshot.return_value = None
    return mock


@pytest.fixture
def mock_pubsub_hub() -> MagicMock:
    """Provides a lightweight mock hub for SSE endpoint tests."""
    hub = MagicMock()
    hub.register.return_value = asyncio.Queue()
    hub.unregister.return_value = None
    return hub


@pytest.fixture
def mock_http_client() -> httpx.AsyncClient:
    """Provides a high-fidelity mock of the httpx.AsyncClient."""
    return create_autospec(httpx.AsyncClient, instance=True)


@pytest.fixture
def mock_public_inference_service() -> PubInferenceService:
    """Provides a high-fidelity mock of the entire PubInferenceService."""
    return create_autospec(PubInferenceService, instance=True)


@pytest.fixture
def mock_model_history_service() -> ModelHistoryService:
    """Provides a high-fidelity mock of the entire ModelHistoryService."""
    return create_autospec(ModelHistoryService, instance=True)


# --- Unit Test SUTs (The "Subjects Under Test" for service logic tests) ---


@pytest.fixture
def unit_test_match_pagination_service(mock_async_session, mock_patch_repository) -> MatchPaginationService:
    """A MatchPaginationService SUT with mocked DB dependencies for unit testing."""
    # Create a simple hero_map for testing
    hero_map = {1: "Anti-Mage", 2: "Crystal Maiden", 3: "Pudge", 4: "Axe"}
    return MatchPaginationService(
        db_session=mock_async_session,
        patch_repository=mock_patch_repository,
        hero_map=hero_map,
    )


@pytest.fixture
def unit_test_redis_pubsub_service(mock_redis_client) -> RedisPubSubService:
    """
    A RedisPubSubService SUT with its underlying Redis client mocked.
    Use this to unit test the logic WITHIN the RedisPubSubService itself.
    """
    return RedisPubSubService(redis_client=mock_redis_client)


@pytest.fixture
def unit_test_public_inference_service(
    mock_model_inference_service,
    mock_db_session_factory,
) -> PubInferenceService:
    """
    A PubInferenceService SUT with mocked model inference service and DB factory.
    """
    return PubInferenceService(
        model_inference_service=mock_model_inference_service,
        db_session_factory=mock_db_session_factory,
    )


# =================================================================================
# LEVEL 2: FIXTURES FOR API LAYER TESTS (Fast, Isolated Integration)
# =================================================================================


@pytest.fixture
def api_layer_app_factory(
    mock_db_session_factory,
    mock_match_pagination_service: MatchPaginationService,
    mock_redis_pubsub_service: RedisPubSubService,
    mock_pubsub_hub: MagicMock,
    mock_http_client: httpx.AsyncClient,
    mock_public_inference_service: PubInferenceService,
    mock_model_history_service: ModelHistoryService,
) -> Callable[[], FastAPI]:
    """
    Provides a factory for a FastAPI app where ALL underlying services
    are replaced with their high-fidelity mock versions.
    """

    def _create_app() -> FastAPI:
        app = FastAPI(title="API Layer Test App")
        app.state.db_session_factory = mock_db_session_factory
        app.state.pubsub_service = mock_redis_pubsub_service
        app.state.pubsub_hub = mock_pubsub_hub

        def override_pagination_service():
            return mock_match_pagination_service

        def override_pubsub_service():
            return mock_redis_pubsub_service

        def override_http_client():
            return mock_http_client

        def override_public_inference_service():
            return mock_public_inference_service

        from api_service.dependencies import get_model_history_service

        app.dependency_overrides[get_match_pagination_service] = override_pagination_service
        app.dependency_overrides[get_pubsub_service] = override_pubsub_service
        app.dependency_overrides[get_http_client] = override_http_client
        app.dependency_overrides[get_public_inference_service] = override_public_inference_service
        app.dependency_overrides[get_model_history_service] = lambda: mock_model_history_service
        return app

    return _create_app


@pytest.fixture
def api_layer_client(
    api_layer_app_factory,
    matches_router,
    inference_router,
    streaming_router,
    mock_prediction_service_api,  # For overriding external API calls
) -> TestClient:
    """
    --- THE DEFAULT CLIENT FOR MOST API TESTS ---
    Provides a single TestClient for the entire app, with all service logic
    completely mocked out. This is fast, reliable, and perfect for testing routing,
    request/response models, and serialization.
    """
    app = api_layer_app_factory()
    app.include_router(matches_router)
    app.include_router(inference_router)
    app.include_router(streaming_router)
    return TestClient(app)


# =================================================================================
# HELPER COMPONENT FIXTURES
# =================================================================================


@pytest.fixture
def matches_router() -> APIRouter:
    from api_service.matches.router import router

    return router


@pytest.fixture
def inference_router() -> APIRouter:
    from api_service.inference.router import router

    return router


@pytest.fixture
def streaming_router() -> APIRouter:
    from api_service.streaming.router import router

    return router


@pytest_asyncio.fixture(scope="function")
async def integration_test_redis_pubsub_service(test_redis_client) -> RedisPubSubService:
    """Provides a real RedisPubSubService backed by the test Redis container."""
    await test_redis_client.flushdb()
    yield RedisPubSubService(redis_client=test_redis_client)
    await test_redis_client.flushdb()
