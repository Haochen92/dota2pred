"""
Event processor-related fixtures for tests.
"""
import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncEngine

# Event processor imports
from dota_oracle.live_pipeline.completion.completion_event_processor import CompletionEventProcessor
from dota_oracle.live_pipeline.data_fetching.new_match_event_processor import NewMatchEventProcessor
from dota_oracle.live_pipeline.feature_engineering.feature_engineering_processor import FeatureEngineeringEventProcessor
from dota_oracle.live_pipeline.prediction.prediction_event_processor import PredictionEventProcessor

# Service imports
from dota_oracle.live_pipeline.services.feature_engineering_service import FeatureEngineeringService
from dota_oracle.live_pipeline.services.feature_preparation_service import FeaturePreparationService
from dota_oracle.live_pipeline.services.history_update_service import HistoryUpdateService
from dota_oracle.live_pipeline.services.match_prediction_service import MatchPredictionService


# ================================
# EVENT PROCESSOR MOCKS (ESSENTIAL!)
# ================================

@pytest.fixture
def mock_new_match_event_processor() -> NewMatchEventProcessor:
    return AsyncMock(spec=NewMatchEventProcessor)


@pytest.fixture
def mock_feature_engineering_event_processor() -> FeatureEngineeringEventProcessor:
    return AsyncMock(spec=FeatureEngineeringEventProcessor)


@pytest.fixture
def mock_prediction_event_processor() -> PredictionEventProcessor:
    return AsyncMock(spec=PredictionEventProcessor)


@pytest.fixture
def mock_completion_event_processor() -> CompletionEventProcessor:
    return AsyncMock(spec=CompletionEventProcessor)


# ================================
# EVENT PROCESSOR COMPONENT FIXTURES
# ================================

@pytest.fixture
def new_match_event_processor(mock_async_engine: AsyncEngine) -> NewMatchEventProcessor:
    return NewMatchEventProcessor(db_engine=mock_async_engine)


@pytest.fixture
def completion_event_processor(mock_history_update_service, mock_async_engine) -> CompletionEventProcessor:
    processor = CompletionEventProcessor(
        db_engine=mock_async_engine,
        history_update_service=mock_history_update_service
    )
    
    return processor


@pytest.fixture
def feature_engineering_event_processor(
    mock_feature_engineering_service: FeatureEngineeringService,
    mock_async_engine: AsyncEngine
) -> FeatureEngineeringEventProcessor:
    return FeatureEngineeringEventProcessor(
        feature_engineering_service=mock_feature_engineering_service,
        db_engine=mock_async_engine
    )


@pytest.fixture
def prediction_event_processor(
    mock_async_engine: AsyncEngine,
    mock_feature_preparation_service: FeaturePreparationService,
    mock_match_prediction_service: MatchPredictionService
) -> PredictionEventProcessor:
    return PredictionEventProcessor(
        db_engine=mock_async_engine,
        feature_preparation_service=mock_feature_preparation_service,
        match_prediction_service=mock_match_prediction_service
    )