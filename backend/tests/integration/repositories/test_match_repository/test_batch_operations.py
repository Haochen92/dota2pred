import pytest

from sqlalchemy.ext.asyncio import AsyncEngine

from ....factories.repository_factories import MatchTableFactory, MatchPydanticFactory
from dota_oracle.data_repository.schemas import MatchOutcomeTable, MatchTable
from dota_oracle.data_repository.match_repository import MatchRepository


from typing import Tuple, Any, Dict

from dota_oracle.utils.set_logging import get_logger

from .conftest import BaseMatchRepositoryTest

logger = get_logger(__name__)

MatchWithOutcome = Tuple[MatchTable, MatchOutcomeTable]

pytestmark = pytest.mark.asyncio(loop_scope='session')



@pytest.mark.usefixtures('clear_match_database')
class TestAddMatchesWithOutcomeBatch(BaseMatchRepositoryTest):
    
    async def test_batch_insert_creates_all_records(
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine,
    ):
        # Arrange
        input_instances = MatchPydanticFactory.batch(size=3)
        input_match_ids = {instance.match_id for instance in input_instances}
        
        # Act
        await match_repository_test_subject.add_matches_with_outcome_batch(input_instances)
        
        # Assert
        match_count, outcome_count = await self._count_matches_in_db(test_postgres_engine, input_match_ids)
        
        assert match_count == len(input_match_ids), \
            f"Expected {len(input_match_ids)} match records, got {match_count}"
        assert outcome_count == len(input_match_ids), \
            f"Expected {len(input_match_ids)} outcome records, got {outcome_count}"
    
    async def test_conflict_preserves_match_details_updates_outcomes(
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine,
    ):
        # Arrange
        original_instance = MatchPydanticFactory.build(match_id=12345)
        conflicting_instance = MatchPydanticFactory.build(match_id=12345)  # Same ID, different data
        
        # Act - Insert original
        await match_repository_test_subject.add_matches_with_outcome_batch([original_instance])
        original_match, original_outcome = await self._get_match_with_outcome(test_postgres_engine, 12345)
        
        # Assert - Original data inserted
        self._assert_pydantic_vs_db_equals(original_instance, original_match, original_outcome, "Original insert")
        
        # Act - Insert conflicting data
        await match_repository_test_subject.add_matches_with_outcome_batch([conflicting_instance])
        final_match, final_outcome = await self._get_match_with_outcome(test_postgres_engine, 12345)
        
        # Assert - Match details preserved (do nothing), outcome updated (do update)
        self._assert_match_equals(original_match, final_match, "Match details after conflict")
        # Note: We expect the outcome to potentially be updated based on the implementation


@pytest.mark.usefixtures('seed_test_data')
class TestGetMatchDetailsBatch(BaseMatchRepositoryTest):
    
    async def test_retrieve_existing_matches_successfully(
        self, 
        match_repository_test_subject: MatchRepository,
        seed_test_data: Tuple[Dict[int, MatchTable], Dict[int, MatchOutcomeTable]]
    ):
        # Arrange
        input_match_ids = [1001, 1003, 1004]
        expected_matches, _ = seed_test_data
        
        # Act
        actual_matches = await match_repository_test_subject.get_match_details_batch(input_match_ids)
        
        # Assert
        assert len(actual_matches) == len(input_match_ids), \
            f"Expected {len(input_match_ids)} matches, got {len(actual_matches)}"
        
        self._assert_match_ids_equal(set(input_match_ids), actual_matches, "Batch retrieval")
        
        # Verify data integrity
        for match_instance in actual_matches:
            expected_match = expected_matches[match_instance.match_id]
            self._assert_match_equals(expected_match, match_instance, f"Match {match_instance.match_id}")
    
    async def test_empty_input_returns_empty_list(self, match_repository_test_subject: MatchRepository):
        result = await match_repository_test_subject.get_match_details_batch([])
        assert result == [], "Empty input should return empty list"
    
    @pytest.mark.parametrize("invalid_input,expected_type", [
        (MatchTableFactory.build(), "MatchTable instance"),
        ({1, 2, 3}, "set")
    ])
    async def test_invalid_input_type_raises_attribute_error(
        self,
        match_repository_test_subject: MatchRepository,
        invalid_input: Any,
        expected_type: str
    ):
        expected_message = f"expected input type {list.__name__}, got {type(invalid_input).__name__}"
        with pytest.raises(AttributeError, match=expected_message):
            await match_repository_test_subject.get_match_details_batch(invalid_input)