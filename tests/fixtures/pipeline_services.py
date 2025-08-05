"""
Pipeline services-related fixtures for tests.
"""

import pytest
from unittest.mock import AsyncMock

# Pipeline Services Import
from live_orchestrator_app.services.feature_engineering_service import FeatureEngineeringService
from live_orchestrator_app.services.feature_preparation_service import FeaturePreparationService
from live_orchestrator_app.services.fetch_outcome_service import FetchOutcomeService
from live_orchestrator_app.services.history_update_service import HistoryUpdateService
from live_orchestrator_app.services.match_prediction_service import MatchPredictionService
from live_orchestrator_app.services.model_inference_service import ModelInferenceService


# ================================
# SERVICE MOCKS (ESSENTIAL!)
# ================================


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


# ================================
# SERVICE COMPONENT FIXTURES
# ================================


@pytest.fixture
def feature_preparation_service(
    mock_model_inference_service, model_meta_data_api_response_factory
) -> FeaturePreparationService:
    mock_model_inference_service.model_metadata = model_meta_data_api_response_factory.build()

    return FeaturePreparationService(mock_model_inference_service)


@pytest.fixture
async def model_inference_service() -> ModelInferenceService:
    service = await ModelInferenceService.create()
    return service
