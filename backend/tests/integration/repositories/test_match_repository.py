import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import delete, select, SQLModel

from ...factories.repository_factories import MatchTableFactory, MatchOutcomeTableFactory, MatchPydanticFactory
from dota_oracle.data_repository.schemas import MatchOutcomeTable, MatchTable
from dota_oracle.data_repository.match_repository import MatchRepository

from dota_oracle.pydantic_models.match import Match as MatchPydantic

from typing import List, Optional, Tuple, Callable, Any, AsyncGenerator, Dict

from dota_oracle.utils.set_logging import get_logger

logger = get_logger(__name__)

MatchWithOutcome = Tuple[MatchTable, MatchOutcomeTable]

pytestmark = pytest.mark.asyncio(loop_scope='session')

@pytest_asyncio.fixture(scope='function')
async def match_repository_test_subject(test_postgres_engine:AsyncEngine):
    return MatchRepository(engine=test_postgres_engine)

@pytest.mark.usefixtures('clear_match_database')
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
            
@pytest.mark.usefixtures('clear_match_database')
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
            
@pytest.mark.usefixtures('clear_match_database')
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

@pytest.mark.usefixtures('seed_test_data')
class TestGetMatchDetailsBatch:
    
    async def test_happy_path(
        self, 
        match_repository_test_subject: MatchRepository,
        seed_test_data: Tuple[Dict[int, MatchTable], Dict[int, MatchOutcomeTable]]
    ):
        # Arrange
        input_match_ids = [1001, 1003, 1004]
        expected_match_details_dict, _ = seed_test_data
        
        # Act
        actual_match_details = await match_repository_test_subject.get_match_details_batch(input_match_ids)        

        # Assert
        assert len(actual_match_details) == len(input_match_ids), \
        f"expected {len(input_match_ids)} matches , got {len(actual_match_details)} matches"
        
        input_match_set = set(input_match_ids)
        actual_match_set = {match.match_id for match in actual_match_details}
        
        assert input_match_set == actual_match_set, \
        f"expected {input_match_set} got {actual_match_set}"
        
        for match_instance in actual_match_details:
            expected_match_instance = expected_match_details_dict[match_instance.match_id]
            for field in MatchTable.model_fields.keys():
                expected_value = getattr(expected_match_instance, field)
                actual_value = getattr(match_instance, field)
                
                assert expected_value == actual_value, (
                    f"value mismatch: expected {expected_value}, got {actual_value}"
                )
    
    async def test_empty_input(self, match_repository_test_subject: MatchRepository):
        test_input = []
        actual_instance = await match_repository_test_subject.get_match_details_batch(test_input)
        
        assert actual_instance == [], f"Expected {[]}, got {actual_instance}"
    
    @pytest.mark.parametrize("test_input", [MatchTableFactory.build(), {1, 2, 3}])
    async def test_invalid_input_type(
        self,
        match_repository_test_subject: MatchRepository,
        test_input: Any
    ):
        expected_message = f"expected input type {list.__name__}, got {type(test_input).__name__}"
        with pytest.raises(AttributeError, match=expected_message) as exec_info:
            await match_repository_test_subject.get_match_details_batch(test_input)
        

@pytest.mark.usefixtures('seed_test_data')
class TestGetMatchDetailsWithOutcome:
    
    @pytest.mark.parametrize(
        "test_id, input_match_id, should_exist",
        [
            ("happy_path", 1001, True),
            ("match_not_found", 9999, False)
        ]
    )
    async def test_get_match_data(
        self, 
        match_repository_test_subject: MatchRepository,
        seed_test_data: Tuple[Dict[int, MatchTable], Dict[int, MatchOutcomeTable]],
        test_id: str,
        input_match_id: int,
        should_exist: bool
    ):
        # ARRANGE
        match_details_dict, match_outcome_dict = seed_test_data
        
        #
        res = await match_repository_test_subject.get_match_details_with_outcome(input_match_id)
        
        if should_exist:
            expected_match_details = match_details_dict[input_match_id]
            expected_match_outcome = match_outcome_dict[input_match_id]
            assert res is not None, f"Expected {res} but got None"
            
            # Assert
            if res:
                actual_match_details, actual_match_outcome = res
                self._assert_equal(
                    test_id, 
                    expected_match_details, 
                    actual_match_details,
                    expected_match_outcome,
                    actual_match_outcome
                )
        else:
            assert res is None, f"Expected None but got {res}"
    
    def _assert_equal(
        self,
        test_id,
        expected_match_details: MatchTable, 
        actual_match_details: MatchTable,
        expected_match_outcome: MatchOutcomeTable,
        actual_match_outcome: MatchOutcomeTable
    ):
        for key in MatchTable.model_fields.keys():
            expected_value = getattr(expected_match_details, key)
            actual_value = getattr(actual_match_details, key)
            
            assert expected_value == actual_value, (
                f"test_id {test_id}: values mismatch"
                f"expected {expected_value}, got {actual_value}"
            )
        
        for key in MatchOutcomeTable.model_fields.keys():
            expected_value = getattr(expected_match_outcome, key)
            actual_value = getattr(actual_match_outcome, key)
            
            assert expected_value == actual_value, (
                f"test_id {test_id}: values mismatch"
                f"expected {expected_value}, got {actual_value}"
            )
        
        

@pytest.mark.usefixtures('seed_test_data')
class TestGetAllMatchDetailsWithOutcome:
    
    async def test_complete_match_data_only(
        self,
        match_repository_test_subject: MatchRepository,
        seed_test_data: Tuple[Dict[int, MatchTable], Dict[int, MatchOutcomeTable]]
    ):
        # Arrange
        match_table_dict, match_outcome_dict = seed_test_data
        
        # Act
        res = await match_repository_test_subject.get_all_match_details_with_outcome()
        expected_match_ids = set(match_table_dict.keys()) & set(match_outcome_dict.keys()) # intersect of 2 sets
        assert len(res) == len(expected_match_ids), f"expected {len(expected_match_ids)} matches, got {len(res)}"
        
        for match_table, match_outcome in res:
            match_id = match_table.match_id
            
            assert match_id in expected_match_ids, \
                f"Unexpected match_id {match_id} in results, expected set {expected_match_ids}"
            
            expected_match_instance = match_table_dict.get(match_id)
            expected_match_outcome = match_outcome_dict.get(match_id)
            
            assert match_table == expected_match_instance, \
            f"expected match_details, {expected_match_instance}, got {match_table}"
            
            assert match_outcome == expected_match_outcome, \
            f"expected match_outcome, {expected_match_outcome}, got {match_outcome}"
    
        
@pytest_asyncio.fixture(scope='function')
async def seed_test_data(test_postgres_engine: AsyncEngine) -> AsyncGenerator[Tuple[Dict[int, MatchTable], Dict[int, MatchOutcomeTable]], None]:
    match_instance_id = [1001, 1002, 1003, 1004, 1005] # seed partials
    match_outcome_id = [1001, 1002, 1003, 1004]
    
    match_instances = [MatchTableFactory.build(match_id=match_id) for match_id in match_instance_id]
    match_outcome_instances = [MatchOutcomeTableFactory.build(match_id=match_id) for match_id in match_outcome_id]
    
    match_dict = {instance.match_id: instance for instance in match_instances}
    match_outcome_dict = {instance.match_id: instance for instance in match_outcome_instances}
    
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():                
            match_values = [instance.model_dump() for instance in match_instances]
            match_outcome_values = [instance.model_dump() for instance in match_outcome_instances]
            try:
                stmt = insert(MatchTable).values(match_values)
                stmt2 = insert(MatchOutcomeTable).values(match_outcome_values)
                await session.execute(stmt)
                await session.execute(stmt2)
            except Exception as e:
                raise e
            
            logger.info(f"Seeding complete")
    
    yield (match_dict, match_outcome_dict)
    
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(MatchTable))
            await session.execute(delete(MatchOutcomeTable))


# Clean up between each test
@pytest_asyncio.fixture(scope='function')
async def clear_match_database(test_postgres_engine: AsyncEngine):
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(MatchTable))
            await session.execute(delete(MatchOutcomeTable))
            

    