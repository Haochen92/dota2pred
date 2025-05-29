import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import delete, select

from ....factories.repository_factories import MatchOutcomeTableFactory, MatchTableFactory
from dota_oracle.data_repository.schemas import MatchOutcomeTable, MatchTable
from dota_oracle.data_repository.match_repository import MatchRepository

from dota_oracle.pydantic_models.match import Match as MatchPydantic

from typing import List, Tuple, Any, AsyncGenerator, Dict, Set

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