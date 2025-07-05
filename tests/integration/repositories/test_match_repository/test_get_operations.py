import pytest


from dota_oracle_common.models.match import MatchOutcomeTable, MatchTable
from dota_oracle_common.repositories.match_repository import MatchRepository


from typing import Tuple, Dict, List

from dota_oracle_common.utils.set_logging import get_logger

from ..base_test_repository import BaseTestRepository

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestGetMatchDetailsWithOutcome:

    @pytest.mark.parametrize(
        "test_scenario,input_match_ids",
        [
            ("get_single_match", [1001]),
            ("get_multiple_matches", [1001, 1002, 1003]),
        ],
    )
    async def test_get_completed_matches_with_relationships(
        self,
        match_repository_test_subject: MatchRepository,
        test_repository: BaseTestRepository,
        seed_test_data: Tuple[Dict[int, MatchTable], Dict[int, MatchOutcomeTable]],
        test_scenario: str,
        input_match_ids: List[int],
    ):
        # Arrange
        match_details_dict, match_outcome_dict = seed_test_data

        # Act
        results = await match_repository_test_subject.get_match_details(
            input_id_list=input_match_ids, relationship_fields=["outcome"]
        )

        test_repository._assert_count_equal(len(results), len(input_match_ids), test_scenario)

        for curr_instance in results:
            match_id = curr_instance.match_id

            expected_match = match_details_dict[match_id]
            expected_outcome = match_outcome_dict[match_id]

            assert curr_instance.outcome is not None, "match outcome relationship missing"

            # actual_match = MatchTable.model_validate(curr_instance)
            # actual_outcome = MatchTable.model_validate(curr_instance.outcome)

            test_repository._assert_equal(expected_match, curr_instance, test_scenario)
            test_repository._assert_equal(expected_outcome, curr_instance.outcome, test_scenario)

    async def test_invalid_match_ids(
        self,
        match_repository_test_subject: MatchRepository,
    ):
        input_match_ids = [8888, 9999]  # non seeded data
        results = await match_repository_test_subject.get_match_details(
            input_id_list=input_match_ids,
        )

        assert results == [], f"test_invalid_match_ids, expected [], got {results}"

    async def test_empty_input_return_all(
        self,
        match_repository_test_subject: MatchRepository,
        test_repository: BaseTestRepository,
        seed_test_data,
    ):
        # Arrange
        expected_match_details_dict, _ = seed_test_data

        # Act
        results = await match_repository_test_subject.get_match_details()

        # Assert
        test_repository._assert_count_equal(len(expected_match_details_dict), len(results), "empty input returns all")

    async def test_get_incompleted_matches_with_relationships(
        self,
        match_repository_test_subject: MatchRepository,
        test_repository: BaseTestRepository,
        seed_test_data,
    ):
        # Arrange
        expected_match_details_dict, _ = seed_test_data

        # Act
        results = await match_repository_test_subject.get_match_details(
            input_id_list=[1005], relationship_fields=["outcome"]  # no match oucome,
        )

        test_repository._assert_count_equal(len(results), 1, "match with no outcome")

        expected_match_instance = expected_match_details_dict[1005]
        actual_match_instance = results[0]

        assert not actual_match_instance.outcome, "Outcome should be missing"

        test_repository._assert_equal(expected_match_instance, actual_match_instance, "match with no outcome")
