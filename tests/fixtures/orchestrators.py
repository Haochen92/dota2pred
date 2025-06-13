"""
Orchestrator-related fixtures for tests.
"""
import pytest
from unittest.mock import AsyncMock

# Orchestrator imports
from live_orchestrator_app.completion.completion_orchestrator import CompletionOrchestrator
from live_orchestrator_app.data_fetching.new_match_orchestrator import NewMatchOrchestrator
from live_orchestrator_app.feature_engineering.feature_engineering_orchestrator import FeatureEngineeringOrchestrator
from live_orchestrator_app.prediction.prediction_orchestrator import PredictionOrchestrator

# Component imports
from live_orchestrator_app.completion.completion_data_provider import CompletionDataProvider
from live_orchestrator_app.completion.completion_event_processor import CompletionEventProcessor
from live_orchestrator_app.data_fetching.new_match_data_provider import NewMatchDataProvider
from live_orchestrator_app.data_fetching.new_match_event_processor import NewMatchEventProcessor
from live_orchestrator_app.feature_engineering.feature_engineering_data_provider import FeatureEngineeringDataProvider
from live_orchestrator_app.feature_engineering.feature_engineering_processor import FeatureEngineeringEventProcessor
from live_orchestrator_app.prediction.prediction_data_provider import PredictionDataProvider
from live_orchestrator_app.prediction.prediction_event_processor import PredictionEventProcessor

# Service imports
from live_orchestrator_app.services.redis_service import RedisService
from live_orchestrator_app.services.history_update_service import HistoryUpdateService


# ================================
# ORCHESTRATOR MOCKS (ESSENTIAL!)
# ================================

@pytest.fixture
def mock_new_match_orchestrator() -> NewMatchOrchestrator:
    return AsyncMock(spec=NewMatchOrchestrator)


@pytest.fixture
def mock_feature_engineering_orchestrator() -> FeatureEngineeringOrchestrator:
    return AsyncMock(spec=FeatureEngineeringOrchestrator)


@pytest.fixture
def mock_prediction_orchestrator() -> PredictionOrchestrator:
    return AsyncMock(spec=PredictionOrchestrator)


@pytest.fixture
def mock_completion_orchestrator() -> CompletionOrchestrator:
    return AsyncMock(spec=CompletionOrchestrator)


# ================================
# ORCHESTRATOR COMPONENT FIXTURES
# ================================

@pytest.fixture
def new_match_orchestrator(
    new_match_data_provider: NewMatchDataProvider,
    new_match_event_processor: NewMatchEventProcessor,
    mock_redis_service: RedisService
) -> NewMatchOrchestrator:
    return NewMatchOrchestrator(
        data_provider=new_match_data_provider,
        event_processor=new_match_event_processor,
        redis_service=mock_redis_service
    )


@pytest.fixture
def feature_engineering_orchestrator(
    mock_redis_service: RedisService,
    feature_engineering_data_provider: FeatureEngineeringDataProvider,
    feature_engineering_event_processor: FeatureEngineeringEventProcessor
) -> FeatureEngineeringOrchestrator:
    return FeatureEngineeringOrchestrator(
        redis_service=mock_redis_service,
        data_provider=feature_engineering_data_provider,
        event_processor=feature_engineering_event_processor
    )


@pytest.fixture
def prediction_orchestrator(
    mock_redis_service: RedisService,
    prediction_data_provider: PredictionDataProvider,
    prediction_event_processor: PredictionEventProcessor
) -> PredictionOrchestrator:
    return PredictionOrchestrator(
        redis_service=mock_redis_service,
        data_provider=prediction_data_provider,
        event_processor=prediction_event_processor
    )


@pytest.fixture
def completion_orchestrator(
    mock_redis_service: RedisService,
    mock_history_update_service: HistoryUpdateService,
    mock_completion_data_provider: CompletionDataProvider,
    mock_completion_event_processor: CompletionEventProcessor
) -> CompletionOrchestrator:
    return CompletionOrchestrator(
        redis_service=mock_redis_service,
        history_update_service=mock_history_update_service,
        completion_data_provider=mock_completion_data_provider,
        completion_event_processor=mock_completion_event_processor
    )