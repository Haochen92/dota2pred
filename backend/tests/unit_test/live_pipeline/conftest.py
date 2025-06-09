import pytest_asyncio
from unittest.mock import AsyncMock

from dota_oracle.live_pipeline.services.feature_preparation_service import FeaturePreparationService
from dota_oracle.inference.model_inference_service import ModelInferenceService
from ...factories.unit_test_factory import ModelMetaDataAPIResponseFactory





@pytest_asyncio.fixture
async def feature_preparation_service():
    mock_service = AsyncMock(spec=ModelInferenceService)
    mock_service.model_metadata = ModelMetaDataAPIResponseFactory.build()
    
    return FeaturePreparationService(mock_service)