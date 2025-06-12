import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from dota_oracle.data_repository.features_repository import FeaturesRepository
from dota_oracle.utils import TaskRunner

from dota_oracle.live_pipeline.services.feature_engineering_service import FeatureEngineeringService

F_PATH = "dota_oracle.live_pipeline.services.feature_engineering_service"


@pytest.mark.asyncio
async def test_create_and_store_features_sucessfully(
    mock_async_session,
    match_table_factory,
    hero_features_table_factory,
    team_features_table_factory,
    player_hero_feature_table_factory,
    mocker,
):
    # Arrange
    mock_logger = mocker.patch(f"{F_PATH}.logger")
    mock_store_features = mocker.patch.object(FeaturesRepository, 'store_features')
    mock_task_runner = mocker.patch.object(TaskRunner, 'run_as_group')
    
    match_instance = match_table_factory.build(match_id=123)
    
    # Mock static method
    mock_heroes_creator = mocker.patch(f'{F_PATH}.HeroesFeatureCreator.create_hero_features')
    mock_heroes_creator.return_value = [hero_features_table_factory.build(match_id=123)]
    
    mock_team_feature_creator = AsyncMock()
    mock_team_feature_creator.create_team_features.return_value = [team_features_table_factory.build(match_id=123)]
    mock_player_hero_feature_creator = AsyncMock()
    mock_player_hero_feature_creator.create_player_hero_features.return_value = [player_hero_feature_table_factory.build(match_id=123)]
    
    feature_engineering_service = FeatureEngineeringService(
        team_feature_creator=mock_team_feature_creator,
        player_hero_feature_creator=mock_player_hero_feature_creator
    )
    
    # Act

    await feature_engineering_service.create_and_store_features(
        match_instance=match_instance,
        session=mock_async_session
    )
    
    # Assert
    mock_team_feature_creator.create_team_features.assert_awaited_once_with(
        mock_async_session, [match_instance]
    )
    mock_player_hero_feature_creator.create_player_hero_features.assert_awaited_once_with(
        mock_async_session, [match_instance]
    )
    mock_heroes_creator.assert_called_once_with([match_instance])
    
    mock_task_runner.assert_awaited_once()
    assert mock_store_features.call_count == 3
    
    mock_logger.debug.assert_called_once_with(
        f"Successfully stored all features for match {match_instance.match_id}"
    )
    

    
@pytest.mark.asyncio
async def test_missing_feature_raise_error(
    mock_async_session,
    match_table_factory,
    team_features_table_factory,
    player_hero_feature_table_factory,
    mocker,
):
    # Arrange
    
    match_instance = match_table_factory.build(match_id=123)
    
    # Mock static method
    mock_heroes_creator = mocker.patch(f'{F_PATH}.HeroesFeatureCreator.create_hero_features')
    mock_heroes_creator.return_value = None
    
    mock_team_feature_creator = AsyncMock()
    mock_team_feature_creator.create_team_features.return_value = team_features_table_factory.build(match_id=123)
    mock_player_hero_feature_creator = AsyncMock()
    mock_player_hero_feature_creator.create_player_hero_features.return_value = player_hero_feature_table_factory.build(match_id=123)
    
    feature_engineering_service = FeatureEngineeringService(
        team_feature_creator=mock_team_feature_creator,
        player_hero_feature_creator=mock_player_hero_feature_creator
    )
    
    # Act
    with pytest.raises(ValueError, match="Incomplete features, raising"):
        await feature_engineering_service.create_and_store_features(
            match_instance=match_instance,
            session=mock_async_session
        )
        
    
    