"""
Tests for get operations: get_feature_by_id, get_all_features_from_table
"""
import pytest
from typing import Dict, Any, Type

from dota_oracle.data_repository.features_repository import FeaturesRepository
from dota_oracle.data_repository.schemas import (
    PlayerHeroFeatureTable,
    TeamFeaturesTable,
    HeroFeaturesTable,
)

from .conftest import BaseFeaturesRepositoryTest, T

pytestmark = pytest.mark.asyncio(loop_scope='session')


class TestGetFeatureById(BaseFeaturesRepositoryTest):
    """Test retrieving individual features by match_id."""
    
    @pytest.mark.parametrize(
        "test_scenario,match_id,feature_class,expected_fields",
        [
            (
                "get_team_features_successfully",
                1001,
                TeamFeaturesTable,
                {
                    "match_id": 1001,
                    "radiant_dire_matchup": 0.65,
                    "radiant_win_rate": 0.4,
                    "dire_win_rate": 0.8
                }
            ),
            (
                "get_hero_features_successfully",
                1003,
                HeroFeaturesTable,
                {
                    "match_id": 1003,
                    "hero_picks": ['mirana', 'windrunner', 'crystal_maiden']
                }
            ),
            (
                "get_player_hero_features_successfully",
                1003,
                PlayerHeroFeatureTable,
                {
                    "match_id": 1003,
                    "player_hero_0_win_rate": 0.1,
                    "player_hero_1_win_rate": 0.2,
                    "player_hero_2_win_rate": 0.3,
                    "player_hero_3_win_rate": 0.4,
                    "player_hero_4_win_rate": 0.5,
                    "player_hero_128_win_rate": 0.6,
                    "player_hero_129_win_rate": 0.7,
                    "player_hero_130_win_rate": 0.8,
                    "player_hero_131_win_rate": 0.9,
                    "player_hero_132_win_rate": 1.0
                }
            )
        ]
    )
    @pytest.mark.usefixtures("seed_features_data")
    async def test_get_existing_feature_returns_correct_data(
        self,
        features_repository_test_subject: FeaturesRepository,
        test_scenario: str,
        match_id: int,
        feature_class: Type[T],
        expected_fields: Dict[str, Any]
    ):
        """Test retrieving existing features by ID returns correct data."""
        # Act
        actual_instance = await features_repository_test_subject.get_feature_by_id(match_id, feature_class)
        
        # Assert
        assert actual_instance is not None, f"{test_scenario}: Expected feature but got None"
        self._assert_feature_fields_match(actual_instance, expected_fields, test_scenario)
    
    @pytest.mark.usefixtures("seed_features_data")
    async def test_get_nonexistent_feature_returns_none(
        self,
        features_repository_test_subject: FeaturesRepository
    ):
        """Test that getting non-existent feature returns None."""
        # Act
        result = await features_repository_test_subject.get_feature_by_id(99999, TeamFeaturesTable)
        
        # Assert  
        assert result is None, "Expected None for non-existent feature"
    
    @pytest.mark.parametrize(
        "test_scenario,match_id,feature_class,expected_error_message",
        [
            ("missing_match_id", None, HeroFeaturesTable, "missing match_id"),
            ("missing_table_class", 1003, None, "missing feature_table_class"),
            ("invalid_class_type", 1003, dict, "feature_table_class must be a subclass of SQLModel")
        ]
    )
    @pytest.mark.usefixtures("seed_features_data")
    async def test_invalid_inputs_raise_value_errors(
        self,
        features_repository_test_subject: FeaturesRepository,
        test_scenario: str,
        match_id: int,
        feature_class: Type[T],
        expected_error_message: str
    ):
        """Test that invalid inputs raise appropriate ValueError with expected message."""
        with pytest.raises(ValueError, match=expected_error_message):
            await features_repository_test_subject.get_feature_by_id(match_id, feature_class)


class TestGetAllFeaturesFromTable(BaseFeaturesRepositoryTest):
    """Test retrieving all features from a table."""
    
    @pytest.mark.parametrize(
        "test_scenario,feature_class,expected_count",
        [
            ("get_all_team_features", TeamFeaturesTable, 2),
            ("get_all_hero_features", HeroFeaturesTable, 1),  
            ("get_all_player_hero_features", PlayerHeroFeatureTable, 1),
        ]
    )
    @pytest.mark.usefixtures("seed_features_data")
    async def test_get_all_features_returns_correct_count(
        self,
        features_repository_test_subject: FeaturesRepository,
        test_scenario: str,
        feature_class: Type[T],
        expected_count: int
    ):
        """Test that get_all_features returns expected number of records."""
        # Act
        actual_features = await features_repository_test_subject.get_all_features_from_table(feature_class)
        
        # Assert
        self._assert_feature_count_equals(expected_count, actual_features, test_scenario)
    
    @pytest.mark.usefixtures("seed_features_data")
    async def test_get_all_team_features_data_integrity(
        self,
        features_repository_test_subject: FeaturesRepository
    ):
        """Test that get_all_features returns data with correct values."""
        # Act
        team_features = await features_repository_test_subject.get_all_features_from_table(TeamFeaturesTable)
        
        # Assert
        assert len(team_features) == 2, "Expected 2 team features"
        
        # Find specific features by match_id
        feature_1001 = next((f for f in team_features if f.match_id == 1001), None)
        feature_1002 = next((f for f in team_features if f.match_id == 1002), None)
        
        assert feature_1001 is not None, "Expected feature for match_id 1001"
        assert feature_1002 is not None, "Expected feature for match_id 1002"
        
        # Verify specific values
        assert feature_1001.radiant_dire_matchup == 0.65
        assert feature_1001.radiant_win_rate == 0.4
        assert feature_1001.dire_win_rate == 0.8
        
        assert feature_1002.radiant_dire_matchup == 0.53
        assert feature_1002.radiant_win_rate == 0.6
        assert feature_1002.dire_win_rate == 0.4
    
    @pytest.mark.usefixtures("clear_features_database")
    async def test_get_all_features_empty_table_returns_empty_list(
        self,
        features_repository_test_subject: FeaturesRepository
    ):
        """Test that get_all_features returns empty list when table is empty."""
        # Act
        result = await features_repository_test_subject.get_all_features_from_table(TeamFeaturesTable)
        
        # Assert
        assert result == [], "Expected empty list for empty table"
    
    async def test_get_all_features_invalid_table_class_raises_error(
        self,
        features_repository_test_subject: FeaturesRepository
    ):
        """Test that invalid table class raises appropriate error."""
        with pytest.raises((ValueError, TypeError)):
            await features_repository_test_subject.get_all_features_from_table(dict)  # type: ignore