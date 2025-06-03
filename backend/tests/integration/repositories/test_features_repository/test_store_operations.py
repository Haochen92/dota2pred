"""
Tests for store operations: store_features
"""
import pytest
import pytest_asyncio
from typing import Dict, Any, Type, List

from dota_oracle.data_repository.features_repository import FeaturesRepository
from ....factories.repository_factories import (
    PlayerHeroFeatureTableFactory,
    TeamFeaturesTableFactory,
    HeroFeaturesTableFactory,
)
from dota_oracle.models.features import (
    PlayerHeroFeatureTable,
    TeamFeaturesTable,
    HeroFeaturesTable,
)

from ..base_test_repository import BaseTestRepository, T

pytestmark = pytest.mark.asyncio(loop_scope='session')

@pytest.mark.usefixtures('seed_features_data')
class TestStoreFeatures:
    """Test storing different types of features to database."""
    
    @pytest.mark.parametrize(
        "test_scenario,feature_instances,table_class",
        [
            (
                "store_single_hero_feature_new",
                [HeroFeaturesTableFactory.build(match_id=1011)], # seeded match only
                HeroFeaturesTable,
            ),
            (
                "store_multiple_team_feature_new",
                [
                    TeamFeaturesTableFactory.build(match_id=1011), # seeded match only
                    TeamFeaturesTableFactory.build(match_id=1012),
                ],
                TeamFeaturesTable,
            ),
            (
                "store_player_hero_features_on_conflict_update",
                [
                    PlayerHeroFeatureTableFactory.build(match_id=1001), # seeded match and feature
                ],
                PlayerHeroFeatureTable,
            ),
        ]
    )
    async def test_store_feature_successfully(
        self,
        features_repository_test_subject: FeaturesRepository,
        test_repository: BaseTestRepository,
        seed_features_data: Dict[str, Dict[int, Any]],
        test_scenario: str,
        feature_instances: List[T],
        table_class: Type[T],
    ):
        """Test storing various types of features successfully."""
        # Arrange
        expected_instance_dict = {instance.match_id: instance for instance in feature_instances}
        
        # Act
        await features_repository_test_subject.store_features(feature_instances, table_class)
        actual_instance_list = await test_repository._get_data(
            model_class=table_class,
            id_filters=list(expected_instance_dict.keys())
        )
        
        # Assert 
        test_repository._assert_count_equal(len(expected_instance_dict), len(actual_instance_list), test_scenario)
        
        for curr_instance in actual_instance_list:
            match_id = curr_instance.match_id
            expected_instance = expected_instance_dict[match_id]
            
            test_repository._assert_equal(expected_instance, curr_instance, test_scenario)

    async def test_store_empty_list_handles_gracefully(
        self,
        features_repository_test_subject: FeaturesRepository
    ):
        """Test that storing empty list handles gracefully without errors."""
        # Should not raise an exception and should return without doing anything
        await features_repository_test_subject.store_features([], TeamFeaturesTable)
        await features_repository_test_subject.store_features([], HeroFeaturesTable)
        await features_repository_test_subject.store_features([], PlayerHeroFeatureTable)
    