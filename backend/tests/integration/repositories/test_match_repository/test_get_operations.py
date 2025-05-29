import pytest

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlmodel import delete

from dota_oracle.data_repository.schemas import MatchOutcomeTable, MatchTable
from dota_oracle.data_repository.match_repository import MatchRepository


from typing import Tuple,Dict

from dota_oracle.utils.set_logging import get_logger

from .conftest import BaseMatchRepositoryTest

logger = get_logger(__name__)

MatchWithOutcome = Tuple[MatchTable, MatchOutcomeTable]

pytestmark = pytest.mark.asyncio(loop_scope='session')



@pytest.mark.usefixtures('seed_test_data')
class TestGetMatchDetailsWithOutcome(BaseMatchRepositoryTest):
    
    @pytest.mark.parametrize(
        "test_scenario,input_match_id,should_exist",
        [
            ("existing_complete_match", 1001, True),
            ("non_existent_match", 9999, False),
            ("details_only_match", 1005, False)  # Has details but no outcome
        ]
    )
    async def test_get_match_with_outcome_scenarios(
        self, 
        match_repository_test_subject: MatchRepository,
        seed_test_data: Tuple[Dict[int, MatchTable], Dict[int, MatchOutcomeTable]],
        test_scenario: str,
        input_match_id: int,
        should_exist: bool
    ):
        # Arrange
        match_details_dict, match_outcome_dict = seed_test_data
        
        # Act
        result = await match_repository_test_subject.get_match_details_with_outcome(input_match_id)
        
        # Assert
        if should_exist:
            assert result is not None, f"{test_scenario}: Expected result but got None"
            
            expected_match = match_details_dict[input_match_id]
            expected_outcome = match_outcome_dict[input_match_id]
            actual_match, actual_outcome = result
            
            self._assert_match_equals(expected_match, actual_match, test_scenario)
            self._assert_outcome_equals(expected_outcome, actual_outcome, test_scenario)
        else:
            assert result is None, f"{test_scenario}: Expected None but got {result}"


@pytest.mark.usefixtures('seed_test_data')
class TestGetAllMatchDetailsWithOutcome(BaseMatchRepositoryTest):
    
    async def test_returns_only_complete_matches_excluding_partials(
        self,
        match_repository_test_subject: MatchRepository,
        seed_test_data: Tuple[Dict[int, MatchTable], Dict[int, MatchOutcomeTable]]
    ):
        # Arrange
        match_table_dict, match_outcome_dict = seed_test_data
        expected_complete_ids = set(match_table_dict.keys()) & set(match_outcome_dict.keys())
        
        logger.info(f"Expected complete match IDs: {expected_complete_ids}")
        logger.info(f"Details-only IDs: {set(match_table_dict.keys()) - set(match_outcome_dict.keys())}")
        
        # Act
        result = await match_repository_test_subject.get_all_match_details_with_outcome()
        
        # Assert
        assert len(result) == len(expected_complete_ids), \
            f"Expected {len(expected_complete_ids)} complete matches, got {len(result)}"
        
        returned_ids = {match_table.match_id for match_table, _ in result}
        assert returned_ids == expected_complete_ids, \
            f"Expected IDs {expected_complete_ids}, got {returned_ids}"
        
        # Verify data integrity for each returned match
        for match_table, match_outcome in result:
            match_id = match_table.match_id
            expected_match = match_table_dict[match_id]
            expected_outcome = match_outcome_dict[match_id]
            
            self._assert_match_equals(expected_match, match_table, f"Match {match_id}")
            self._assert_outcome_equals(expected_outcome, match_outcome, f"Outcome {match_id}")
    
    async def test_empty_database_returns_empty_list(
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine
    ):
        # Arrange - Ensure database is empty
        async with AsyncSession(test_postgres_engine) as session:
            async with session.begin():
                await session.execute(delete(MatchTable))
                await session.execute(delete(MatchOutcomeTable))
        
        # Act
        result = await match_repository_test_subject.get_all_match_details_with_outcome()
        
        # Assert
        assert result == [], "Empty database should return empty list"