import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, ANY

import pandas as pd
import numpy as np

from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.data_repository.heroes_repository import HeroesRepository

from dota_oracle.feature_transformation import FeatureEncoder
from dota_oracle.inference.model_inference_service import ModelInferenceService


from ...factories.repository_factories import (
    TeamFeaturesTableFactory, PlayerHeroFeatureTableFactory,
    HeroFeaturesTableFactory, MatchTableFactory
)

from dota_oracle.live_pipeline.services.feature_preparation_service import FeaturePreparationService

from ...factories.unit_test_factory import ModelMetaDataAPIResponseFactory, ModelPredictionAPIResponseFactory

F_PATH = "dota_oracle.live_pipeline.services.feature_preparation_service"

@pytest.mark.asyncio
async def test_prepare_features_for_inference(feature_preparation_service, mock_async_session, mocker):
    
    # Arrange
    
    # Mock variables
    match_id = 123
    mock_df = pd.DataFrame([{"match_id":"12345"}])
    mock_np = np.array([1,2,3,4])
    
    # Mock repository
    mock_match_repo = AsyncMock(spec=MatchRepository)
    mock_hero_repo = AsyncMock(spec=HeroesRepository)
    
    # Mock database response
    mock_db_response = (
        TeamFeaturesTableFactory.build(match_id=match_id),
        HeroFeaturesTableFactory.build(match_id=match_id),
        PlayerHeroFeatureTableFactory.build(match_id=match_id)
    )
    
    mock_get_features = mocker.patch.object(
        FeaturePreparationService, 
        '_get_features_from_db', 
        return_value=mock_db_response
    )
    
    mock_encode_features = mocker.patch.object(
        FeaturePreparationService, 
        "_encode_hero_feature", 
        return_value=mock_df
    )
    
    # FIX: Use patch.object for instance methods
    mock_merge_and_filter = mocker.patch.object(
        FeaturePreparationService, 
        '_merge_and_filter_dataframe', 
        return_value=mock_df
    )
    
    # FIX: Mock pandas DataFrame.to_numpy method instead
    mock_to_numpy = mocker.patch.object(
        pd.DataFrame, 
        'to_numpy', 
        return_value=mock_np
    )
    
    # Act
    res = await feature_preparation_service.prepare_features_for_inference(
        match_id=match_id,
        db_session=mock_async_session
    )
    
    assert res.tolist() == mock_np.tolist() # compare arrays by converting to list
    
    mock_get_features.assert_awaited_once()
    mock_encode_features.assert_awaited_once()
    mock_merge_and_filter.assert_called_once()
    mock_to_numpy.assert_called_once()

    

@pytest_asyncio.fixture
async def model_inference_service():
    service = ModelInferenceService()
    
    # Just set the attribute directly - bypass the async initialization
    service.model_metadata = ModelMetaDataAPIResponseFactory.build()
    
    return service

@pytest_asyncio.fixture
async def feature_preparation_service(model_inference_service):
    return FeaturePreparationService(model_inference_service)