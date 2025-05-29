import pytest

from sqlalchemy.ext.asyncio import AsyncEngine

from ....factories.repository_factories import MatchTableFactory, MatchOutcomeTableFactory
from dota_oracle.data_repository.schemas import MatchOutcomeTable, MatchTable
from dota_oracle.data_repository.match_repository import MatchRepository



from typing import Tuple, Any

from dota_oracle.utils.set_logging import get_logger

from .conftest import BaseMatchRepositoryTest

logger = get_logger(__name__)

MatchWithOutcome = Tuple[MatchTable, MatchOutcomeTable]

pytestmark = pytest.mark.asyncio(loop_scope='session')


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