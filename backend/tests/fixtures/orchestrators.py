"""
Orchestrator-related fixtures for tests.
"""
import pytest
from unittest.mock import AsyncMock

# Orchestrator imports
from dota_oracle.live_pipeline.completion.completion_orchestrator import CompletionOrchestrator
from dota_oracle.live_pipeline.data_fetching.new_match_orchestrator import NewMatchOrchestrator
from dota_oracle.live_pipeline.feature_engineering.feature_engineering_orchestrator import FeatureEngineeringOrchestrator
from dota_oracle.live_pipeline.prediction.prediction_orchestrator import PredictionOrchestrator

# Component imports
from dota_oracle.live_pipeline.completion.completion_data_provider import CompletionDataProvider
from dota_oracle.live_pipeline.completion.completion_event_processor import CompletionEventProcessor
from dota_oracle.live_pipeline.data_fetching.new_match_data_provider import NewMatchDataProvider
from dota_oracle.live_pipeline.data_fetching.new_match_event_processor import NewMatchEventProcessor
from dota_oracle.live_pipeline.feature_engineering.feature_engineering_data_provider import FeatureEngineeringDataProvider
from dota_oracle.live_pipeline.feature_engineering.feature_engineering_processor import FeatureEngineeringEventProcessor
from dota_oracle.live_pipeline.prediction.prediction_data_provider import PredictionDataProvider
from dota_oracle.live_pipeline.prediction.prediction_event_processor import PredictionEventProcessor

# Service imports
from dota_oracle.live_pipeline.services.redis_service import RedisService
from dota_oracle.live_pipeline.services.history_update_service import HistoryUpdateService


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