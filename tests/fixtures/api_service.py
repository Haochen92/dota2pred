"""
API Service-related fixtures for tests.

This file is organized by the PURPOSE of the fixtures, following a clear hierarchy:
1.  MOCK FIXTURES: Provide high-level mocks of services or low-level clients.
    These are used as dependencies for unit tests.

2.  UNIT TEST SUTs (Subjects Under Test): Provide instances of our services
    with all their dependencies mocked. Used for fast, isolated business logic tests.

3.  INTEGRATION TEST SUTs: Provide instances of our services connected to real
    test infrastructure (e.g., a Redis Docker container). Used to test integration
    with external technologies.

4.  API-LAYER FIXTURES: Provide the FastAPI app, routers, and fully configured
    TestClients for API integration testing.
"""

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from fastapi import FastAPI, APIRouter
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from testcontainers.redis import RedisContainer

# Import actual dependencies for type-safe overrides
from api_service.dependencies import get_match_pagination_service, get_pubsub_service
from api_service.matches.match_pagination_service import MatchPaginationService
from api_service.streaming.redis_pubsub_service import RedisPubSubService


# =================================================================================
# TIER 1: MOCK FIXTURES (For Unit Testing)
# =================================================================================


@pytest.fixture
def mock_redis_pubsub_service() -> RedisPubSubService:
    """Provides a high-level mock of the entire RedisPubSubService."""
    mock = AsyncMock(spec=RedisPubSubService)
    mock.publish_live_update = AsyncMock()  # Explicitly mock async methods for clarity
    return mock


# =================================================================================
# TIER 2: UNIT TEST SUBJECTS (SUTs) - (Business Logic Testing)
# =================================================================================


@pytest.fixture
def unit_test_match_pagination_service(
    mock_async_session, mock_heroes_repository, mock_patch_repository
) -> MatchPaginationService:
    """Provides a MatchPaginationService instance with all DB dependencies mocked."""
    return MatchPaginationService(
        db_session=mock_async_session,
        hero_repository=mock_heroes_repository,
        patch_repository=mock_patch_repository,
    )


@pytest.fixture
def unit_test_redis_pubsub_service(mock_redis_client) -> RedisPubSubService:
    """Provides a RedisPubSubService instance with the underlying Redis client mocked."""
    return RedisPubSubService(redis_client=mock_redis_client)


# =================================================================================
# TIER 3: INTEGRATION TEST SUBJECTS (SUTs) - (Technology Integration Testing)
# =================================================================================


@pytest_asyncio.fixture
async def integration_test_redis_pubsub_service(redis_container_instance: RedisContainer):
    """
    Provides a RedisPubSubService instance connected to a REAL test Redis container.
    """
    host = redis_container_instance.get_container_host_ip()
    port = redis_container_instance.get_exposed_port(6379)
    pool = aioredis.ConnectionPool(host=host, port=int(port), decode_responses=True)
    service_redis_client = aioredis.Redis(connection_pool=pool)
    service = RedisPubSubService(redis_client=service_redis_client)
    yield service
    await pool.disconnect()


@pytest_asyncio.fixture
async def integration_test_match_pagination_service(
    db_session, hero_repository_test_subject, patch_repository_test_subject
) -> MatchPaginationService:
    """
    Provides a MatchPaginationService instance connected to a REAL test database and repositories.
    """
    return MatchPaginationService(
        db_session=db_session,
        hero_repository=hero_repository_test_subject,
        patch_repository=patch_repository_test_subject,
    )


# =================================================================================
# TIER 4: API-LAYER FIXTURES (API Integration Testing)
# =================================================================================

# --- Core Components ---


@pytest.fixture
def mock_fastapi_app(mock_db_session_factory) -> FastAPI:
    """Provides the base FastAPI app object with core state, but NO routers."""
    app = FastAPI(title="Test API")
    app.state.db_session_factory = mock_db_session_factory
    return app


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


# --- Assembled Apps with Overrides ---


@pytest.fixture
def app_with_matches_router(
    mock_fastapi_app: FastAPI, matches_router: APIRouter, unit_test_match_pagination_service: MatchPaginationService
) -> FastAPI:
    """Assembles an app with the 'matches' router and its dependencies overridden."""

    def override():
        return unit_test_match_pagination_service

    mock_fastapi_app.dependency_overrides[get_match_pagination_service] = override
    mock_fastapi_app.include_router(matches_router)
    yield mock_fastapi_app
    del mock_fastapi_app.dependency_overrides[get_match_pagination_service]


@pytest.fixture
def app_with_inference_router(mock_fastapi_app: FastAPI, inference_router: APIRouter) -> FastAPI:
    """Assembles an app with the 'inference' router."""
    mock_fastapi_app.include_router(inference_router)
    yield mock_fastapi_app


@pytest.fixture
def app_with_streaming_router(
    mock_fastapi_app: FastAPI, streaming_router: APIRouter, mock_redis_pubsub_service
) -> FastAPI:
    """Assembles an app with the 'streaming' router and its dependencies overridden."""

    def override():
        return mock_redis_pubsub_service

    mock_fastapi_app.dependency_overrides[get_pubsub_service] = override
    mock_fastapi_app.include_router(streaming_router)
    yield mock_fastapi_app
    del mock_fastapi_app.dependency_overrides[get_pubsub_service]


# --- Test Clients (The final products for API tests) ---


@pytest.fixture
def matches_client(app_with_matches_router: FastAPI) -> TestClient:
    """Provides a TestClient for the fully configured 'matches' API."""
    return TestClient(app_with_matches_router)


@pytest.fixture
def inference_client(app_with_inference_router: FastAPI) -> TestClient:
    """Provides a TestClient for the 'inference' API."""
    return TestClient(app_with_inference_router)


@pytest.fixture
def streaming_client(app_with_streaming_router: FastAPI) -> TestClient:
    """Provides a TestClient for the fully configured 'streaming' API."""
    return TestClient(app_with_streaming_router)
