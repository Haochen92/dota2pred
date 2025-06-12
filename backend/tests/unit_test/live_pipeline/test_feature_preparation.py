import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, ANY, MagicMock

import pandas as pd
import numpy as np


from dota_oracle.models.match import MatchTable
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.data_repository.heroes_repository import HeroesRepository

from dota_oracle.feature_transformation import FeatureEncoder
from dota_oracle.inference.model_inference_service import ModelInferenceService



from dota_oracle.live_pipeline.services.feature_preparation_service import FeaturePreparationService


F_PATH = "dota_oracle.live_pipeline.services.feature_preparation_service"

@pytest.mark.asyncio
async def test_prepare_features_for_inference(feature_preparation_service, mock_async_session, mocker, team_features_table_factory, hero_features_table_factory, player_hero_feature_table_factory):
    
    # Arrange
    
    # Mock variables
    match_id = 123
    mock_df = pd.DataFrame([{"match_id":"12345"}])
    mock_np = np.array([1,2,3,4])
    
    # Mock database response
    mock_db_response = (
        team_features_table_factory.build(match_id=match_id),
        hero_features_table_factory.build(match_id=match_id),
        player_hero_feature_table_factory.build(match_id=match_id)
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

    
@pytest.mark.asyncio
async def test_get_features_from_db(feature_preparation_service, mocker, team_features_table_factory, hero_features_table_factory, player_hero_feature_table_factory):
    # Arrange
    match_id = 123
    mock_team_features = team_features_table_factory.build(match_id=match_id)
    mock_hero_features = hero_features_table_factory.build(match_id=match_id)
    mock_player_hero_features = player_hero_feature_table_factory.build(match_id=match_id)
    mock_match_repository = AsyncMock(spec=MatchRepository)
    
     # Create a mock match instance with the required attributes
    mock_match_instance = MagicMock()
    mock_match_instance.team_features = mock_team_features
    mock_match_instance.hero_features = mock_hero_features
    mock_match_instance.player_hero_features = mock_player_hero_features
    
    
    mock_get_match_details = mocker.patch.object(
        mock_match_repository,
        'get_match_details',
        return_value=[mock_match_instance]
    )
    
    # Act
    
    res = await feature_preparation_service._get_features_from_db(
        match_id=match_id,
        match_repository=mock_match_repository
    )
    
    # Assert
    
    assert (mock_team_features, mock_hero_features, mock_player_hero_features) == res
    
    mock_get_match_details.assert_awaited_once_with(
        input_id_list=[match_id],
        relationship_fields=["team_features", "player_hero_features", "hero_features"],
        limit=1
    )
    

    
    