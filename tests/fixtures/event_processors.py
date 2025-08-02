"""
Event processor-related fixtures for tests.
"""

import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import async_sessionmaker

# Event processor imports
from live_orchestrator_app.completion.completion_event_processor import CompletionEventProcessor
from live_orchestrator_app.data_fetching.new_match_event_processor import NewMatchEventProcessor
from live_orchestrator_app.feature_engineering.feature_engineering_processor import FeatureEngineeringEventProcessor
from live_orchestrator_app.prediction.prediction_event_processor import PredictionEventProcessor

# Service imports
from live_orchestrator_app.services.feature_engineering_service import FeatureEngineeringService
from live_orchestrator_app.services.feature_preparation_service import FeaturePreparationService
from live_orchestrator_app.services.match_prediction_service import MatchPredictionService


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
def new_match_event_processor(mock_async_session) -> NewMatchEventProcessor:
    mock_session_factory = AsyncMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__.return_value = mock_async_session
    mock_session_factory.return_value.__aexit__.return_value = None
    return NewMatchEventProcessor(db_session_factory=mock_session_factory)


@pytest.fixture
def completion_event_processor(mock_history_update_service, mock_async_session) -> CompletionEventProcessor:
    mock_session_factory = AsyncMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__.return_value = mock_async_session
    mock_session_factory.return_value.__aexit__.return_value = None
    processor = CompletionEventProcessor(
        db_session_factory=mock_session_factory, history_update_service=mock_history_update_service
    )

    return processor


@pytest.fixture
def feature_engineering_event_processor(
    mock_feature_engineering_service: FeatureEngineeringService, mock_async_session
) -> FeatureEngineeringEventProcessor:
    mock_session_factory = AsyncMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__.return_value = mock_async_session
    mock_session_factory.return_value.__aexit__.return_value = None
    return FeatureEngineeringEventProcessor(
        feature_engineering_service=mock_feature_engineering_service, db_session_factory=mock_session_factory
    )


@pytest.fixture
def prediction_event_processor(
    mock_async_session,
    mock_feature_preparation_service: FeaturePreparationService,
    mock_match_prediction_service: MatchPredictionService,
) -> PredictionEventProcessor:
    mock_session_factory = AsyncMock(spec=async_sessionmaker)
    mock_session_factory.return_value.__aenter__.return_value = mock_async_session
    mock_session_factory.return_value.__aexit__.return_value = None
    return PredictionEventProcessor(
        db_session_factory=mock_session_factory,
        feature_preparation_service=mock_feature_preparation_service,
        match_prediction_service=mock_match_prediction_service,
    )
