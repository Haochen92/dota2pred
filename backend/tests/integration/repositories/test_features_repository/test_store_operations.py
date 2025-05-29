"""
Tests for store operations: store_features
"""
import pytest
from typing import Dict, Any, Type
from polyfactory.factories.pydantic_factory import ModelFactory

from dota_oracle.data_repository.features_repository import FeaturesRepository
from ....factories.repository_factories import (
    PlayerHeroFeatureTableFactory,
    TeamFeaturesTableFactory,
    HeroFeaturesTableFactory,
)
from dota_oracle.data_repository.schemas import (
    PlayerHeroFeatureTable,
    TeamFeaturesTable,
    HeroFeaturesTable,
)

from .conftest import BaseFeaturesRepositoryTest, T

pytestmark = pytest.mark.asyncio(loop_scope='session')


class TestStoreFeatures(BaseFeaturesRepositoryTest):
    """Test storing different types of features to database."""
    
    @pytest.mark.parametrize(
        "test_scenario,factory_class,table_class,feature_data",
        [
            (
                "store_hero_features_new_match",
                HeroFeaturesTableFactory,
                HeroFeaturesTable,
                {
                    'match_id': 1011,
                    'hero_picks': ["pangolier", "puck", "windranger"]
                }
            ),
            (
                "store_hero_features_existing_match_upsert",
                HeroFeaturesTableFactory,
                HeroFeaturesTable,
                {
                    'match_id': 1003,
                    'hero_picks': ["drow_ranger", "anti_mage", "spectre"]
                }
            ),
            (
                "store_team_features_new_match",
                TeamFeaturesTableFactory,
                TeamFeaturesTable,
                {
                    'match_id': 1011, 
                    'radiant_dire_matchup': 0.7,
                    'radiant_win_rate': 0.4,
                    'dire_win_rate': 0.5
                }
            ),
            (
                "store_player_hero_features_new_match",
                PlayerHeroFeatureTableFactory,
                PlayerHeroFeatureTable,
                {
                    'match_id': 1011,
                    'player_hero_0_win_rate': 0.1,
                    'player_hero_1_win_rate': 0.1,
                    'player_hero_2_win_rate': 0.3,
                    'player_hero_3_win_rate': 0.3,
                    'player_hero_4_win_rate': 0.5,
                    'player_hero_128_win_rate': 0.4,
                    'player_hero_129_win_rate': 0.1,
                    'player_hero_130_win_rate': 0.83,
                    'player_hero_131_win_rate': 0.99,
                    'player_hero_132_win_rate': 0.01,
                }
            ),
        ]
    )
    @pytest.mark.usefixtures("seed_features_data")
    async def test_store_feature_successfully(
        self,
        features_repository_test_subject: FeaturesRepository,
        test_postgres_engine,
        test_scenario: str,
        factory_class: ModelFactory,  
        table_class: Type[T],
        feature_data: Dict[str, Any]
    ):
        """Test storing various types of features successfully."""
        # Arrange
        match_id = feature_data.get('match_id')
        assert match_id is not None, f"{test_scenario}: Test data missing match_id"
        
        input_instance = factory_class.build(**feature_data)
        
        # Act
        await features_repository_test_subject.store_features([input_instance], table_class)
        
        # Assert - verify data was stored correctly
        stored_instance = await self._get_feature_by_id(test_postgres_engine, match_id, table_class)
        self._assert_feature_fields_match(stored_instance, feature_data, test_scenario)
    
    @pytest.mark.usefixtures("seed_features_data")
    async def test_store_multiple_features_batch(
        self,
        features_repository_test_subject: FeaturesRepository,
        test_postgres_engine
    ):
        """Test storing multiple features of the same type in a batch."""
        # Arrange
        team_features = [
            TeamFeaturesTableFactory.build(match_id=1011, radiant_dire_matchup=0.7, radiant_win_rate=0.4),
            TeamFeaturesTableFactory.build(match_id=1012, radiant_dire_matchup=0.6, radiant_win_rate=0.5),
        ]
        
        # Act
        await features_repository_test_subject.store_features(team_features, TeamFeaturesTable)
        
        # Assert
        stored_count = await self._count_features_in_table(test_postgres_engine, TeamFeaturesTable, {1011, 1012})
        assert stored_count == 2, f"Expected 2 features stored, got {stored_count}"
        
        # Verify individual records
        feature_1011 = await self._get_feature_by_id(test_postgres_engine, 1011, TeamFeaturesTable)
        assert feature_1011.radiant_dire_matchup == 0.7
        
        feature_1012 = await self._get_feature_by_id(test_postgres_engine, 1012, TeamFeaturesTable)
        assert feature_1012.radiant_dire_matchup == 0.6
    
    async def test_store_empty_list_handles_gracefully(
        self,
        features_repository_test_subject: FeaturesRepository
    ):
        """Test that storing empty list handles gracefully without errors."""
        # Should not raise an exception and should return without doing anything
        await features_repository_test_subject.store_features([], TeamFeaturesTable)
        await features_repository_test_subject.store_features([], HeroFeaturesTable)
        await features_repository_test_subject.store_features([], PlayerHeroFeatureTable)
    
    @pytest.mark.usefixtures("clear_features_database")
    async def test_store_features_in_empty_database(
        self,
        features_repository_test_subject: FeaturesRepository,
        test_postgres_engine
    ):
        """Test storing features when features database is initially empty (but FKs exist)."""
        # Arrange - Features database is empty but MatchTable has required FKs
        hero_feature = HeroFeaturesTableFactory.build(
            match_id=1001,  # This match_id exists due to FK fixture
            hero_picks=["invoker", "pudge", "sniper"]
        )
        
        # Act
        await features_repository_test_subject.store_features([hero_feature], HeroFeaturesTable)
        
        # Assert
        total_count = await self._count_features_in_table(test_postgres_engine, HeroFeaturesTable)
        assert total_count == 1, f"Expected 1 feature in empty database, got {total_count}"
        
        stored_feature = await self._get_feature_by_id(test_postgres_engine, 1001, HeroFeaturesTable)
        assert stored_feature.hero_picks == ["invoker", "pudge", "sniper"]