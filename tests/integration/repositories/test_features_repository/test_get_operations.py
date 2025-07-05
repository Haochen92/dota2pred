"""
Tests for get operations: get_feature_by_id, get_all_features_from_table
"""

import pytest
from typing import Dict, Any, Type, List, TypeVar, Optional
from sqlmodel import SQLModel

from dota_oracle_common.repositories.features_repository import FeaturesRepository
from dota_oracle_common.models.features import (
    PlayerHeroFeatureTable,
    TeamFeaturesTable,
    HeroFeaturesTable,
)

from ..base_test_repository import BaseTestRepository

pytestmark = pytest.mark.asyncio(loop_scope="session")

T = TypeVar("T", bound=SQLModel)


class TestGetFeatureById:
    """Test retrieving individual features by match_id."""

    @pytest.mark.parametrize(
        ["test_scenario", "input_match_ids", "feature_class", "expected_count", "limit"],
        [
            (
                "get_multiple_team_feature_no_limit",
                [1001, 1002],
                TeamFeaturesTable,
                2,
                None,
            ),
            (
                "get_single_hero_feature_no_limit",
                [1003],
                HeroFeaturesTable,
                1,
                None,
            ),
            (
                "get_single_player_hero_feature_no_limit",
                [1002],
                PlayerHeroFeatureTable,
                1,
                None,
            ),
            (
                "get_all_player_hero_feature_no_limit",
                None,
                PlayerHeroFeatureTable,
                3,
                None,
            ),
            ("empty_list_return_all", [], PlayerHeroFeatureTable, 3, None),
            (
                "get_all_Player_hero_feature_limit_2",
                None,
                PlayerHeroFeatureTable,
                2,
                2,
            ),
        ],
    )
    async def test_successful_get_ops(
        self,
        features_repository_test_subject: FeaturesRepository,
        test_repository: BaseTestRepository,
        seed_features_data: Dict[str, Any],
        test_scenario: str,
        input_match_ids: List[int],
        feature_class: Type[T],
        expected_count: int,
        limit: Optional[int],
    ) -> None:
        """Test retrieving existing features by ID returns correct data."""
        # Arrange
        expected_dict = seed_features_data.get(feature_class.__name__)

        assert expected_dict is not None, f"No seed data found for {feature_class.__name__}"

        # Act
        actual_instance_list: List[T] = await features_repository_test_subject.get_features(
            table_class=feature_class, match_ids=input_match_ids, limit=limit
        )

        # Assert
        test_repository._assert_count_equal(expected_count, len(actual_instance_list), test_scenario)

        for instance in actual_instance_list:
            match_id = instance.match_id  # type: ignore
            expected_instance = expected_dict.get(match_id)

            test_repository._assert_equal(expected_instance, instance, test_scenario)

    async def test_return_empty_list(self, features_repository_test_subject: FeaturesRepository) -> None:
        # Act
        result = await features_repository_test_subject.get_features(
            table_class=TeamFeaturesTable, match_ids=[9999, 10000]
        )

        # Assert
        assert result == [], f"Expected empty list, got {result}"
