import pytest
from unittest.mock import AsyncMock, ANY

# Make sure to import the table classes for type checking in assertions
from dota_oracle_common.models.features import HeroFeaturesTable, TeamFeaturesTable, PlayerHeroFeatureTable
from dota_oracle_common.repositories.features_repository import FeaturesRepository

from live_orchestrator_app.services.feature_engineering_service import FeatureEngineeringService

# The path for mocking needs to point to the location where the objects are USED
F_PATH = "live_orchestrator_app.services.feature_engineering_service"
REPO_F_PATH = "dota_oracle_common.repositories.features_repository"


@pytest.mark.asyncio
async def test_create_and_store_features_sucessfully(
    mock_async_session,
    match_table_factory,
    hero_features_table_factory,
    team_features_table_factory,
    player_hero_feature_table_factory,
    mocker,
) -> None:
    # Arrange
    mock_logger = mocker.patch(f"{F_PATH}.logger")

    mock_store_features = mocker.patch.object(FeaturesRepository, "store_features", new_callable=AsyncMock)

    match_instance = match_table_factory.build(match_id=123)

    # Mock static method
    mock_heroes_creator = mocker.patch(f"{F_PATH}.HeroesFeatureCreator.create_hero_features")
    mock_heroes_creator.return_value = [hero_features_table_factory.build(match_id=123)]

    mock_team_feature_creator = AsyncMock()
    mock_team_feature_creator.create_team_features.return_value = [team_features_table_factory.build(match_id=123)]
    mock_player_hero_feature_creator = AsyncMock()
    mock_player_hero_feature_creator.create_player_hero_features.return_value = [
        player_hero_feature_table_factory.build(match_id=123)
    ]

    feature_engineering_service = FeatureEngineeringService(
        team_feature_creator=mock_team_feature_creator, player_hero_feature_creator=mock_player_hero_feature_creator
    )

    # Act
    await feature_engineering_service.create_and_store_features(
        match_instance=match_instance, session=mock_async_session
    )

    # Assert
    mock_team_feature_creator.create_team_features.assert_awaited_once_with(mock_async_session, [match_instance])
    mock_player_hero_feature_creator.create_player_hero_features.assert_awaited_once_with(
        mock_async_session, [match_instance]
    )
    mock_heroes_creator.assert_called_once_with([match_instance])
    assert mock_store_features.await_count == 3

    mock_store_features.assert_any_await(feature_instances=ANY, table_class=HeroFeaturesTable)
    mock_store_features.assert_any_await(feature_instances=ANY, table_class=TeamFeaturesTable)
    mock_store_features.assert_any_await(feature_instances=ANY, table_class=PlayerHeroFeatureTable)

    mock_logger.debug.assert_called_with(f"Successfully stored all features for match {match_instance.match_id}")


@pytest.mark.asyncio
async def test_missing_feature_raise_error(
    mock_async_session,
    match_table_factory,
    team_features_table_factory,
    player_hero_feature_table_factory,
    mocker,
) -> None:

    # Arrange
    match_instance = match_table_factory.build(match_id=123)

    # Mock static method
    mock_heroes_creator = mocker.patch(f"{F_PATH}.HeroesFeatureCreator.create_hero_features")
    mock_heroes_creator.return_value = None  # Simulate a missing feature

    mock_team_feature_creator = AsyncMock()
    mock_team_feature_creator.create_team_features.return_value = [team_features_table_factory.build(match_id=123)]
    mock_player_hero_feature_creator = AsyncMock()
    mock_player_hero_feature_creator.create_player_hero_features.return_value = [
        player_hero_feature_table_factory.build(match_id=123)
    ]

    feature_engineering_service = FeatureEngineeringService(
        team_feature_creator=mock_team_feature_creator, player_hero_feature_creator=mock_player_hero_feature_creator
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Incomplete features"):
        await feature_engineering_service.create_and_store_features(
            match_instance=match_instance, session=mock_async_session
        )
