"""
Pipeline services-related fixtures for tests.
"""
import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncEngine

# Pipeline Services Import
from dota_oracle.live_pipeline.services.feature_engineering_service import FeatureEngineeringService
from dota_oracle.live_pipeline.services.feature_preparation_service import FeaturePreparationService
from dota_oracle.live_pipeline.services.fetch_outcome_service import FetchOutcomeService
from dota_oracle.live_pipeline.services.history_update_service import HistoryUpdateService
from dota_oracle.live_pipeline.services.match_prediction_service import MatchPredictionService

# ML/Inference imports
from dota_oracle.inference import ModelInferenceService

# Factory imports
from ..factories.unit_test_factory import ModelMetaDataAPIResponseFactory


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
def feature_preparation_service(mock_model_inference_service) -> FeaturePreparationService:
    mock_model_inference_service.model_metadata = ModelMetaDataAPIResponseFactory.build()
    
    return FeaturePreparationService(mock_model_inference_service)


@pytest.fixture
async def model_inference_service() -> ModelInferenceService:
    service = await ModelInferenceService.create()
    return service