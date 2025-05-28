import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import delete, select, SQLModel

from ...factories.repository_factories import MatchTableFactory, MatchOutcomeTableFactory, MatchPydanticFactory
from dota_oracle.data_repository.schemas import MatchOutcomeTable, MatchTable
from dota_oracle.data_repository.match_repository import MatchRepository

from dota_oracle.pydantic_models.match import Match as MatchPydantic

from typing import List, Optional, Tuple, Callable, Any

from dota_oracle.utils.set_logging import get_logger

logger = get_logger(__name__)

MatchWithOutcome = Tuple[MatchTable, MatchOutcomeTable]

pytestmark = pytest.mark.asyncio(loop_scope='session')

@pytest_asyncio.fixture(scope='function')
async def match_repository_test_subject(test_postgres_engine:AsyncEngine):
    return MatchRepository(engine=test_postgres_engine)

class TestInsertMatchDetails:
    
    async def test_happy_path( 
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine
    ):
        # Arrange
        input_instance = MatchTableFactory.build()
        
        # ACT
        await match_repository_test_subject.insert_match_details(input_instance)
        
        actual_instance = await self._get_instance_by_id(test_postgres_engine, input_instance.match_id)
        
        # ASSERT
        self._assert_match_equals(input_instance, actual_instance)
                
                
                    
    async def test_on_conflict_do_nothing( 
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine,
    ):
        # Arrange
        input_instance1 = MatchTableFactory.build(match_id=12345)
        input_instance2 = MatchTableFactory.build(match_id=12345)
        
        # ACT
        await match_repository_test_subject.insert_match_details(input_instance1)
        
        actual_instance = await self._get_instance_by_id(test_postgres_engine, input_instance1.match_id)
        
        # Assert
        self._assert_match_equals(input_instance1, actual_instance)
        
        # ACT         
        await match_repository_test_subject.insert_match_details(input_instance2)
        actual_instance2 = await self._get_instance_by_id(test_postgres_engine, input_instance2.match_id)

        # Assert
        self._assert_match_equals(input_instance1, actual_instance2)
                
                
    @pytest.mark.parametrize('input_data', [MatchTableFactory.batch(3), {"match_id": 10294}, None])
    async def test_invalid_input_data(self, match_repository_test_subject: MatchRepository, input_data: Any):
        with pytest.raises(AttributeError) as exc_info:
            await match_repository_test_subject.insert_match_details(input_data)
    
    async def _get_instance_by_id(
        self, 
        test_postgres_engine: AsyncEngine,
        input_match_id: int
    ) -> MatchTable:
        async with AsyncSession(test_postgres_engine) as session:
            async with session.begin():
                stmt = select(MatchTable).where(MatchTable.match_id == input_match_id)
                result = await session.execute(stmt)
                
                actual_instance = result.scalars().one() # will raise error if not found
                
                session.expunge(actual_instance)
                return actual_instance
        
    def _assert_match_equals(self, expected: MatchTable, actual: MatchTable):
        for col in MatchTable.model_fields.keys():
            expected_value = getattr(expected, col)
            actual_value = getattr(actual, col)
            assert expected_value == actual_value, (
                f"mismatch between values for field {col}: "
                f"expected {expected_value} got {actual_value}"
            )
            

class TestInsertMatchOutcome:
    
    async def test_happy_path( 
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine
    ):
        # Arrange
        input_instance = MatchOutcomeTableFactory.build()
        
        # ACT
        await match_repository_test_subject.insert_match_outcome(input_instance)
        
        actual_instance = await self._get_instance_by_id(test_postgres_engine, input_instance.match_id)
        
        # ASSERT
        self._assert_match_outcome_equals(input_instance, actual_instance)
                
                
                    
    async def test_on_conflict_do_update( 
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine,
    ):
        # Arrange
        input_instance1 = MatchOutcomeTableFactory.build(match_id=12345, radiant_win=True)
        input_instance2 = MatchOutcomeTableFactory.build(match_id=12345, radiant_win=False)
        
        # ACT - Insert first instance
        await match_repository_test_subject.insert_match_outcome(input_instance1)
        
        actual_instance = await self._get_instance_by_id(test_postgres_engine, input_instance1.match_id)
        
        # Assert - First instance inserted correctly
        self._assert_match_outcome_equals(input_instance1, actual_instance)
        
        # ACT - Insert second instance with same match_id but different radiant_win         
        await match_repository_test_subject.insert_match_outcome(input_instance2)
        actual_instance2 = await self._get_instance_by_id(test_postgres_engine, input_instance2.match_id)

        # Assert - Second instance updated the radiant_win field
        self._assert_match_outcome_equals(input_instance2, actual_instance2)
                
                
    @pytest.mark.parametrize('input_data', [MatchOutcomeTableFactory.batch(3), {"match_id": 10294}, None])
    async def test_invalid_input_data(self, match_repository_test_subject: MatchRepository, input_data: Any):
        with pytest.raises(AttributeError) as exc_info:
            await match_repository_test_subject.insert_match_outcome(input_data)
    
    async def _get_instance_by_id(
        self, 
        test_postgres_engine: AsyncEngine,
        input_match_id: int
    ) -> MatchOutcomeTable:
        async with AsyncSession(test_postgres_engine) as session:
            async with session.begin():
                stmt = select(MatchOutcomeTable).where(MatchOutcomeTable.match_id == input_match_id)
                result = await session.execute(stmt)
                
                actual_instance = result.scalars().one() # will raise error if not found
                
                session.expunge(actual_instance)
                return actual_instance
        
    def _assert_match_outcome_equals(self, expected: MatchOutcomeTable, actual: MatchOutcomeTable):
        for col in MatchOutcomeTable.model_fields.keys():
            expected_value = getattr(expected, col)
            actual_value = getattr(actual, col)
            assert expected_value == actual_value, (
                f"mismatch between values for field {col}: "
                f"expected {expected_value} got {actual_value}"
            )

class TestAddMatchesWithOutcomeBatch:
    
    async def test_happy_path(
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine,
    ):
        # Arrange
        input_list_instances = MatchPydanticFactory.batch(size=3)
        input_match_ids = {instance.match_id for instance in input_list_instances}
        
        # Act 
        await match_repository_test_subject.add_matches_with_outcome_batch(input_list_instances)
        
        async with AsyncSession(test_postgres_engine) as session:
            async with session.begin():
                stmt = select(MatchTable).where(MatchTable.match_id.in_(input_match_ids)) # type:ignore
                results = await session.execute(stmt)
                
                actual_instances = results.scalars().all()
                
                # Assert
                assert len(actual_instances) == len(input_match_ids), \
                f"expected {len(input_match_ids)} instances, got {len(actual_instances)}"
                
                stmt = select(MatchOutcomeTable).where(MatchOutcomeTable.match_id.in_(input_match_ids)) # type:ignore
                results = await session.execute(stmt)
                match_outcome_instances = results.scalars().all()
                
                # Assert
                assert len(match_outcome_instances) == len(input_match_ids), \
                f"expected {len(input_match_ids)} instances, got {len(match_outcome_instances)}"
                
    
    async def test_on_conflict_do_nothing(
        self,
        match_repository_test_subject: MatchRepository,
        test_postgres_engine: AsyncEngine,
    ):
        # Arrange
        input_instance1 = MatchPydanticFactory.build()
        test_match_id = input_instance1.match_id
        
        input_instance2 = MatchPydanticFactory.build(match_id=test_match_id)
        
        # Act
        await match_repository_test_subject.add_matches_with_outcome_batch([input_instance1])
    
        match_instance1, match_outcome_instance1 = await self._get_instance(test_postgres_engine, test_match_id)
        
        # Assert
        self._assert_equal(input_instance1, match_instance1, match_outcome_instance1)
        
        # Act
        
        await match_repository_test_subject.add_matches_with_outcome_batch([input_instance2])
        
        match_instance2, match_outcome_instance2 = await self._get_instance(test_postgres_engine, test_match_id)
        
        # Assert
        self._assert_equal(input_instance1, match_instance2, match_outcome_instance2)
        
        
    async def _get_instance(self, test_postgres_engine: AsyncEngine, match_id: int)-> Tuple[MatchTable, MatchOutcomeTable]:
        async with AsyncSession(test_postgres_engine) as session:
            async with session.begin():
                match_result = await session.execute(select(MatchTable).where(MatchTable.match_id == match_id))
                match_instance = match_result.scalars().one()
                
                outcome_result = await session.execute(select(MatchOutcomeTable).where(MatchOutcomeTable.match_id == match_id))
                outcome_instance = outcome_result.scalars().one()
                
                session.expunge_all()
                
                return (match_instance, outcome_instance)
                
                
    def _assert_equal(
        self,
        input_instance: MatchPydantic,
        match_instance: MatchTable,
        outcome_instance: MatchOutcomeTable
    ):
        input_instance_dict = input_instance.model_dump()
        match_instance_dict = match_instance.model_dump()
        outcome_dict = outcome_instance.model_dump()
        
        actual_instance_dict = {**match_instance_dict, **outcome_dict}
        
        for field, expected_value in input_instance_dict.items():
            actual_value = actual_instance_dict.get(field)
            
            assert expected_value == actual_value, (
                f"Value mismatch for field {field}:"
                f"expected {expected_value}, got {actual_value}"
            )
        
        
                

# Clean up between each test
@pytest_asyncio.fixture(scope='function', autouse=True)
async def clear_match_database(test_postgres_engine: AsyncEngine):
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(MatchTable))
            await session.execute(delete(MatchOutcomeTable))
            
    
            
    