"""
Data provider-related fixtures for tests.
"""

import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncEngine

# Data provider imports
from live_orchestrator_app.completion.completion_data_provider import CompletionDataProvider
from live_orchestrator_app.data_fetching.new_match_data_provider import NewMatchDataProvider
from live_orchestrator_app.feature_engineering.feature_engineering_data_provider import FeatureEngineeringDataProvider
from live_orchestrator_app.prediction.prediction_data_provider import PredictionDataProvider

# Service imports
from live_orchestrator_app.services.redis_service import RedisService


# ================================
# DATA PROVIDER MOCKS (ESSENTIAL!)
# ================================


@pytest.fixture
def mock_new_match_data_provider() -> NewMatchDataProvider:
    return AsyncMock(spec=NewMatchDataProvider)


@pytest.fixture
def mock_feature_engineering_data_provider() -> FeatureEngineeringDataProvider:
    return AsyncMock(spec=FeatureEngineeringDataProvider)


@pytest.fixture
def mock_prediction_data_provider() -> PredictionDataProvider:
    return AsyncMock(spec=PredictionDataProvider)


@pytest.fixture
def mock_completion_data_provider() -> CompletionDataProvider:
    return AsyncMock(spec=CompletionDataProvider)


# ================================
# DATA PROVIDER COMPONENT FIXTURES
# ================================


@pytest.fixture
def new_match_data_provider(mock_redis_service: RedisService) -> NewMatchDataProvider:
    return NewMatchDataProvider(redis_service=mock_redis_service)


@pytest.fixture
def feature_engineering_data_provider(
    mock_redis_service: RedisService, mock_async_engine: AsyncEngine
) -> FeatureEngineeringDataProvider:
    return FeatureEngineeringDataProvider(redis_service=mock_redis_service, db_engine=mock_async_engine)


@pytest.fixture
def prediction_data_provider(mock_redis_service: RedisService) -> PredictionDataProvider:
    return PredictionDataProvider(redis_service=mock_redis_service)
