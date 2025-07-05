import pytest

from dota_oracle_common.models.match import MatchOutcomeTable, MatchTable
from dota_oracle_common.repositories.match_repository import MatchRepository

from typing import Tuple, Any

from dota_oracle_common.utils.set_logging import get_logger

from ..base_test_repository import BaseTestRepository

logger = get_logger(__name__)

MatchWithOutcome = Tuple[MatchTable, MatchOutcomeTable]

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestInsertMatchDetails:

    async def test_insert_new_match_successfully(
        self,
        match_repository_test_subject: MatchRepository,
        test_repository: BaseTestRepository,
        match_table_factory,
    ) -> None:
        # Arrange
        input_instance = match_table_factory.build(match_id=2001)

        # Act
        await match_repository_test_subject.insert_match_details([input_instance])

        # Assert
        actual_instance = await test_repository._get_data(model_class=MatchTable, id_filters=[input_instance.match_id])

        test_repository._assert_equal(input_instance, actual_instance[0], "Insert new match")

    async def test_conflict_does_nothing_preserves_original(
        self,
        match_repository_test_subject: MatchRepository,
        test_repository: BaseTestRepository,
        match_table_factory,
    ) -> None:
        # Arrange
        original_instance = match_table_factory.build(match_id=12345)
        conflicting_instance = match_table_factory.build(match_id=12345)  # Same ID, different data

        # Act - Insert original
        await match_repository_test_subject.insert_match_details([original_instance])
        first_result = await test_repository._get_data(model_class=MatchTable, id_filters=[original_instance.match_id])
        test_repository._assert_count_equal(1, len(first_result), "test_conflict_do_nothing")

        actual_instance = first_result[0]
        # Assert - Original inserted correctly
        test_repository._assert_equal(original_instance, actual_instance, "Original insert")

        # Act - Try to insert conflicting instance
        await match_repository_test_subject.insert_match_details([conflicting_instance])
        final_result = await test_repository._get_data(model_class=MatchTable, id_filters=[original_instance.match_id])
        test_repository._assert_count_equal(1, len(final_result), "test_conflict_do_nothing")

        final_instance = final_result[0]
        # Assert - Original data preserved (conflict ignored)
        test_repository._assert_equal(original_instance, final_instance, "After conflict")

    @pytest.mark.parametrize(
        "invalid_input, expected_exception",
        [
            ((1, 2, 3), TypeError),
            ({"match_id": 10294}, TypeError),
        ],
    )
    async def test_invalid_input_raises_attribute_error(
        self, match_repository_test_subject: MatchRepository, invalid_input: Any, expected_exception: type[Exception]
    ) -> None:
        with pytest.raises(expected_exception):
            await match_repository_test_subject.insert_match_details(invalid_input)

    @pytest.mark.parametrize("empty_input", [None, []])
    async def test_handle_empty_value_gracefully(
        self,
        match_repository_test_subject: MatchRepository,
        empty_input: Any,
    ) -> None:
        # should not raise any error
        await match_repository_test_subject.insert_match_details(empty_input)


class TestInsertMatchOutcome:

    async def test_insert_new_outcome_successfully(
        self,
        match_repository_test_subject: MatchRepository,
        test_repository: BaseTestRepository,
        seed_test_data,
        match_outcome_table_factory,
    ) -> None:
        # Arrange
        input_instance = match_outcome_table_factory.build(match_id=1005)  # seeded match but not match_outcome

        # Act
        await match_repository_test_subject.insert_match_outcome([input_instance])

        # Assert
        res = await test_repository._get_data(model_class=MatchOutcomeTable, id_filters=[input_instance.match_id])
        test_repository._assert_count_equal(len(res), 1, "test_insert_new_outcome")

        actual_instance = res[0]

        test_repository._assert_equal(input_instance, actual_instance, "Insert new outcome")

    async def test_conflict_do_nothing_radiant_win_field(
        self,
        match_repository_test_subject: MatchRepository,
        test_repository: BaseTestRepository,
        seed_test_data,
        match_outcome_table_factory,
    ) -> None:
        # Arrange
        original_instance = match_outcome_table_factory.build(
            match_id=1006, radiant_win=True
        )  # seeded match but not outcome
        update_instance = match_outcome_table_factory.build(match_id=1006, radiant_win=False)

        # Act - Insert original
        await match_repository_test_subject.insert_match_outcome([original_instance])
        first_result = await test_repository._get_data(
            model_class=MatchOutcomeTable, id_filters=[original_instance.match_id]
        )
        test_repository._assert_count_equal(1, len(first_result), "test_conflict_updates")
        first_instance = first_result[0]

        # Assert - Original inserted correctly
        test_repository._assert_equal(original_instance, first_instance, "Original insert")

        # Act - Insert (should retain original value)
        await match_repository_test_subject.insert_match_outcome([update_instance])
        final_result = await test_repository._get_data(
            model_class=MatchOutcomeTable, id_filters=[update_instance.match_id]
        )
        test_repository._assert_count_equal(1, len(final_result), "New insert")
        final_instance = final_result[0]

        # Assert - Data values remains unchanged
        test_repository._assert_equal(first_instance, final_instance, "After upsert")

    @pytest.mark.parametrize(
        "invalid_input, expected_exception",
        [
            ((1, 2, 3), TypeError),
            ({"match_id": 10294}, TypeError),
        ],
    )
    async def test_invalid_input_raises_attribute_error(
        self,
        match_repository_test_subject: MatchRepository,
        invalid_input: Any,
        expected_exception: type[Exception],
    ) -> None:
        with pytest.raises(expected_exception):
            await match_repository_test_subject.insert_match_outcome(invalid_input)

    @pytest.mark.parametrize("empty_input", [None, []])
    async def test_handle_empty_value_gracefully(
        self,
        match_repository_test_subject: MatchRepository,
        empty_input: Any,
    ) -> None:
        # should not raise any error
        await match_repository_test_subject.insert_match_outcome(empty_input)
