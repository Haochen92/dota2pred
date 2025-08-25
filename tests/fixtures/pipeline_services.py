"""
Fixtures for the Live Orchestrator App tests.

This file is organized by the PURPOSE of the fixtures, following a clear hierarchy:
1.  MOCK FIXTURES: Provide high-level mocks of services.
2.  UNIT TEST SUTs (Subjects Under Test): Provide service instances with their
    dependencies mocked. Used for fast, isolated business logic tests.
3.  INTEGRATION TEST SUTs: Provide service instances connected to real
    test infrastructure (e.g., a Redis Docker container).
"""

import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from testcontainers.redis import RedisContainer
from unittest.mock import AsyncMock

# Pipeline Services Import
from live_orchestrator_app.services.feature_engineering_service import FeatureEngineeringService
from live_orchestrator_app.services.feature_preparation_service import FeaturePreparationService
from live_orchestrator_app.services.fetch_outcome_service import FetchOutcomeService
from live_orchestrator_app.services.history_update_service import HistoryUpdateService
from live_orchestrator_app.services.match_prediction_service import MatchPredictionService
from dota_oracle_pipeline.inference.model_inference_service import ModelInferenceService
from live_orchestrator_app.services.stale_match_service import StaleMatchService
from live_orchestrator_app.services.notifications_service import NotificationService
from live_orchestrator_app.redis_services.redis_service import RedisService

# Feature Transformation Components
from dota_oracle_pipeline.feature_transformation.feature_encoder import FeatureEncoder

# Endpoint configurations
from dota_oracle_common.constants.endpoint_configs import service_url


# =================================================================================
# TIER 1: MOCK FIXTURES (For Unit Testing)
# =================================================================================


@pytest.fixture
def mock_feature_engineering_service() -> FeatureEngineeringService:
    return AsyncMock(spec=FeatureEngineeringService)


@pytest.fixture
def mock_history_update_service() -> HistoryUpdateService:
    return AsyncMock(spec=HistoryUpdateService)


@pytest.fixture
def mock_match_prediction_service() -> MatchPredictionService:
    return AsyncMock(spec=MatchPredictionService)


@pytest.fixture
def mock_feature_preparation_service() -> FeaturePreparationService:
    return AsyncMock(spec=FeaturePreparationService)


@pytest.fixture
def mock_model_inference_service() -> ModelInferenceService:
    return AsyncMock(spec=ModelInferenceService)


@pytest.fixture
def mock_fetch_outcome_service() -> FetchOutcomeService:
    return AsyncMock(spec=FetchOutcomeService)


@pytest.fixture
def mock_stale_match_service() -> StaleMatchService:
    return AsyncMock(spec=StaleMatchService)


@pytest.fixture
def mock_notification_service() -> NotificationService:
    return AsyncMock(spec=NotificationService)


@pytest.fixture
def mock_redis_service() -> RedisService:
    return AsyncMock(spec=RedisService)


@pytest.fixture
def mock_feature_encoder() -> FeatureEncoder:
    return AsyncMock(spec=FeatureEncoder)


# =================================================================================
# TIER 2: UNIT TEST SUBJECTS (SUTs) - (Business Logic Testing)
# =================================================================================


@pytest.fixture
def unit_test_feature_encoder() -> FeatureEncoder:
    """Provides a FeatureEncoder instance for unit testing with a simple hero map."""
    # Create a simple hero map for testing
    test_hero_map = {1: "hero_1", 2: "hero_2", 3: "hero_3"}
    return FeatureEncoder(test_hero_map)


@pytest.fixture
def unit_test_feature_preparation_service(
    model_meta_data_api_response_factory, mock_feature_encoder
) -> FeaturePreparationService:
    """Provides a FeaturePreparationService instance for unit testing."""
    return FeaturePreparationService(model_meta_data_api_response_factory.build(), feature_encoder=mock_feature_encoder)


@pytest.fixture
def unit_test_model_inference_service(mock_http_client, model_meta_data_api_response_factory) -> ModelInferenceService:
    """Provides a ModelInferenceService instance with a mocked HTTP client."""
    return ModelInferenceService(
        http_client=mock_http_client,
        model_metadata=model_meta_data_api_response_factory.build(),
        prediction_url=service_url.PRO_MATCHES_INFERENCE_URL,
    )


@pytest.fixture
def unit_test_notification_service(
    mock_redis_service, mock_db_session_factory, mock_http_client
) -> NotificationService:
    """Provides a NotificationService instance with all external dependencies mocked."""
    return NotificationService(
        redis_service=mock_redis_service, db_session_factory=mock_db_session_factory, http_client=mock_http_client
    )


@pytest.fixture
def unit_test_redis_service(mock_redis_client) -> RedisService:
    """Provides a RedisService instance with the underlying Redis client mocked."""
    return RedisService(redis_client=mock_redis_client)


# =================================================================================
# TIER 3: INTEGRATION TEST SUBJECTS (SUTs) - (Technology Integration Testing)
# =================================================================================


@pytest_asyncio.fixture
async def integration_test_redis_service(redis_container_instance: RedisContainer) -> RedisService:
    """
    Provides a RedisService instance connected to a REAL test Redis container.
    """
    host = redis_container_instance.get_container_host_ip()
    port = redis_container_instance.get_exposed_port(6379)
    pool = aioredis.ConnectionPool(host=host, port=int(port), decode_responses=True)
    service_redis_client = aioredis.Redis(connection_pool=pool)

    service = RedisService(redis_client=service_redis_client)
    await service.initialize_async_service()
    yield service
    await pool.disconnect()
