import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import delete, select, SQLModel

from ...factories.repository_factories import MatchTableFactory, MatchOutcomeTableFactory, MatchPydanticFactory
from dota_oracle.data_repository.schemas import MatchOutcomeTable, MatchTable
from dota_oracle.data_repository.match_repository import MatchRepository

from dota_oracle.pydantic_models.match import Match as MatchPydantic

from typing import List, Optional, Tuple, Callable, Any, AsyncGenerator, Dict, Set

from dota_oracle.utils.set_logging import get_logger

logger = get_logger(__name__)

MatchWithOutcome = Tuple[MatchTable, MatchOutcomeTable]

pytestmark = pytest.mark.asyncio(loop_scope='session')


# ========================
# BASE TEST CLASS
# ========================

class BaseMatchRepositoryTest:
    """Base class with common assertion helpers and database operations."""
    
    # Database Operation Helpers
    async def _get_match_by_id(self, engine: AsyncEngine, match_id: int) -> MatchTable:
        """Retrieve a single MatchTable instance by match_id."""
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(MatchTable).where(MatchTable.match_id == match_id)
                result = await session.execute(stmt)
                instance = result.scalars().one()
                session.expunge(instance)
                return instance
    
    async def _get_outcome_by_id(self, engine: AsyncEngine, match_id: int) -> MatchOutcomeTable:
        """Retrieve a single MatchOutcomeTable instance by match_id."""
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(MatchOutcomeTable).where(MatchOutcomeTable.match_id == match_id)
                result = await session.execute(stmt)
                instance = result.scalars().one()
                session.expunge(instance)
                return instance
    
    async def _get_match_with_outcome(self, engine: AsyncEngine, match_id: int) -> Tuple[MatchTable, MatchOutcomeTable]:
        """Retrieve both MatchTable and MatchOutcomeTable for a given match_id."""
        async with AsyncSession(engine) as session:
            async with session.begin():
                match_result = await session.execute(select(MatchTable).where(MatchTable.match_id == match_id))
                match_instance = match_result.scalars().one()
                
                outcome_result = await session.execute(select(MatchOutcomeTable).where(MatchOutcomeTable.match_id == match_id))
                outcome_instance = outcome_result.scalars().one()
                
                session.expunge_all()
                return (match_instance, outcome_instance)
    
    async def _count_matches_in_db(self, engine: AsyncEngine, match_ids: Set[int]) -> Tuple[int, int]:
        """Count how many matches and outcomes exist in DB for given match_ids."""
        async with AsyncSession(engine) as session:
            async with session.begin():
                match_stmt = select(MatchTable).where(MatchTable.match_id.in_(match_ids))
                outcome_stmt = select(MatchOutcomeTable).where(MatchOutcomeTable.match_id.in_(match_ids))
                
                match_results = await session.execute(match_stmt)
                outcome_results = await session.execute(outcome_stmt)
                
                match_count = len(match_results.scalars().all())
                outcome_count = len(outcome_results.scalars().all())
                
                return match_count, outcome_count
    
    # Assertion Helpers
    def _assert_match_equals(self, expected: MatchTable, actual: MatchTable, context: str = ""):
        """Compare MatchTable instances field by field."""
        excluded_fields = {'_sa_instance_state'}
        
        for field in MatchTable.model_fields.keys():
            if field in excluded_fields:
                continue
                
            expected_value = getattr(expected, field)
            actual_value = getattr(actual, field)
            assert expected_value == actual_value, (
                f"{context} - Match field '{field}' mismatch: "
                f"expected {expected_value}, got {actual_value}"
            )
    
    def _assert_outcome_equals(self, expected: MatchOutcomeTable, actual: MatchOutcomeTable, context: str = ""):
        """Compare MatchOutcomeTable instances field by field."""
        excluded_fields = {'_sa_instance_state'}
        
        for field in MatchOutcomeTable.model_fields.keys():
            if field in excluded_fields:
                continue
                
            expected_value = getattr(expected, field)
            actual_value = getattr(actual, field)
            assert expected_value == actual_value, (
                f"{context} - Outcome field '{field}' mismatch: "
                f"expected {expected_value}, got {actual_value}"
            )
    
    def _assert_pydantic_vs_db_equals(
        self, 
        pydantic_instance: MatchPydantic, 
        match_instance: MatchTable, 
        outcome_instance: MatchOutcomeTable,
        context: str = ""
    ):
        """Compare Pydantic instance against DB match + outcome instances."""
        pydantic_dict = pydantic_instance.model_dump()
        match_dict = match_instance.model_dump()
        outcome_dict = outcome_instance.model_dump()
        
        combined_db_dict = {**match_dict, **outcome_dict}
        
        for field, expected_value in pydantic_dict.items():
            actual_value = combined_db_dict.get(field)
            assert expected_value == actual_value, (
                f"{context} - Field '{field}' mismatch: "
                f"expected {expected_value}, got {actual_value}"
            )
    
    def _assert_match_ids_equal(self, expected_ids: Set[int], actual_matches: List[Any], context: str = ""):
        """Assert that actual matches contain exactly the expected match_ids."""
        actual_ids = {getattr(match, 'match_id') if not isinstance(match, tuple) else match[0].match_id 
                      for match in actual_matches}
        
        assert actual_ids == expected_ids, (
            f"{context} - Match ID mismatch: expected {expected_ids}, got {actual_ids}"
        )


# ========================
# FIXTURES
# ========================

@pytest_asyncio.fixture(scope='function')
async def match_repository_test_subject(test_postgres_engine: AsyncEngine):
    return MatchRepository(engine=test_postgres_engine)

@pytest_asyncio.fixture(scope='function')
async def clear_match_database(test_postgres_engine: AsyncEngine):
    """Clean up database between tests."""
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(MatchTable))
            await session.execute(delete(MatchOutcomeTable))

@pytest_asyncio.fixture(scope='function')
async def seed_test_data(test_postgres_engine: AsyncEngine) -> AsyncGenerator[Tuple[Dict[int, MatchTable], Dict[int, MatchOutcomeTable]], None]:
    """Seed database with partial data for testing joins."""
    match_instance_ids = [1001, 1002, 1003, 1004, 1005]  # 5 matches with details
    match_outcome_ids = [1001, 1002, 1003, 1004]         # 4 matches with outcomes
    
    match_instances = [MatchTableFactory.build(match_id=match_id) for match_id in match_instance_ids]
    match_outcome_instances = [MatchOutcomeTableFactory.build(match_id=match_id) for match_id in match_outcome_ids]
    
    match_dict = {instance.match_id: instance for instance in match_instances}
    match_outcome_dict = {instance.match_id: instance for instance in match_outcome_instances}
    
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():                
            match_values = [instance.model_dump() for instance in match_instances]
            match_outcome_values = [instance.model_dump() for instance in match_outcome_instances]
            
            await session.execute(insert(MatchTable).values(match_values))
            await session.execute(insert(MatchOutcomeTable).values(match_outcome_values))
            
            logger.info(f"Seeded {len(match_instances)} match details and {len(match_outcome_instances)} outcomes")
    
    yield (match_dict, match_outcome_dict)
    
    # Cleanup
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(MatchTable))
            await session.execute(delete(MatchOutcomeTable))


# ========================
# TEST CLASSES
# ========================

@pytest.mark.usefixtures('clear_match_database')
class TestInsertMatchDetails(BaseMatchRepositoryTest):
    
    async def test_insert_new_match_successfully(
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine
    ):
        # Arrange
        input_instance = MatchTableFactory.build()
        
        # Act
        await match_repository_test_subject.insert_match_details(input_instance)
        
        # Assert
        actual_instance = await self._get_match_by_id(test_postgres_engine, input_instance.match_id)
        self._assert_match_equals(input_instance, actual_instance, "Insert new match")
    
    async def test_conflict_does_nothing_preserves_original(
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine,
    ):
        # Arrange
        original_instance = MatchTableFactory.build(match_id=12345)
        conflicting_instance = MatchTableFactory.build(match_id=12345)  # Same ID, different data
        
        # Act - Insert original
        await match_repository_test_subject.insert_match_details(original_instance)
        first_result = await self._get_match_by_id(test_postgres_engine, original_instance.match_id)
        
        # Assert - Original inserted correctly
        self._assert_match_equals(original_instance, first_result, "Original insert")
        
        # Act - Try to insert conflicting instance
        await match_repository_test_subject.insert_match_details(conflicting_instance)
        final_result = await self._get_match_by_id(test_postgres_engine, original_instance.match_id)
        
        # Assert - Original data preserved (conflict ignored)
        self._assert_match_equals(original_instance, final_result, "After conflict")
    
    @pytest.mark.parametrize('invalid_input', [
        MatchTableFactory.batch(3),  # List instead of single instance
        {"match_id": 10294},         # Dict instead of model
        None                         # None value
    ])
    async def test_invalid_input_raises_attribute_error(
        self, 
        match_repository_test_subject: MatchRepository, 
        invalid_input: Any
    ):
        with pytest.raises(AttributeError):
            await match_repository_test_subject.insert_match_details(invalid_input)


@pytest.mark.usefixtures('clear_match_database')
class TestInsertMatchOutcome(BaseMatchRepositoryTest):
    
    async def test_insert_new_outcome_successfully(
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine
    ):
        # Arrange
        input_instance = MatchOutcomeTableFactory.build()
        
        # Act
        await match_repository_test_subject.insert_match_outcome(input_instance)
        
        # Assert
        actual_instance = await self._get_outcome_by_id(test_postgres_engine, input_instance.match_id)
        self._assert_outcome_equals(input_instance, actual_instance, "Insert new outcome")
    
    async def test_conflict_updates_radiant_win_field(
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine,
    ):
        # Arrange
        original_instance = MatchOutcomeTableFactory.build(match_id=12345, radiant_win=True)
        update_instance = MatchOutcomeTableFactory.build(match_id=12345, radiant_win=False)
        
        # Act - Insert original
        await match_repository_test_subject.insert_match_outcome(original_instance)
        first_result = await self._get_outcome_by_id(test_postgres_engine, original_instance.match_id)
        
        # Assert - Original inserted correctly
        self._assert_outcome_equals(original_instance, first_result, "Original insert")
        
        # Act - Insert update (should upsert)
        await match_repository_test_subject.insert_match_outcome(update_instance)
        final_result = await self._get_outcome_by_id(test_postgres_engine, update_instance.match_id)
        
        # Assert - Data updated with new radiant_win value
        self._assert_outcome_equals(update_instance, final_result, "After upsert")
    
    @pytest.mark.parametrize('invalid_input', [
        MatchOutcomeTableFactory.batch(3),
        {"match_id": 10294},
        None
    ])
    async def test_invalid_input_raises_attribute_error(
        self, 
        match_repository_test_subject: MatchRepository, 
        invalid_input: Any
    ):
        with pytest.raises(AttributeError):
            await match_repository_test_subject.insert_match_outcome(invalid_input)


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