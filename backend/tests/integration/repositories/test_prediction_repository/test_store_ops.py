import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import delete, select

from ....factories.repository_factories import MatchPredictionTableFactory
from dota_oracle.data_repository.schemas import MatchPredictionTable
from dota_oracle.data_repository.prediction_repository import PredictionRepository


from typing import List, Tuple, Any, AsyncGenerator, Dict, Set

from dota_oracle.utils.set_logging import get_logger

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session')


class TestStoreMatchPrediction:
    
    async def test_happy_path(
        self,
        prediction_repository_test_subject: PredictionRepository,
        test_postgres_engine: AsyncEngine
    ):
        test_instance = MatchPredictionTableFactory.build(
            match_id = 12345, # primary key
            predictor_name = 'random_model' # primary key
        )
        
        await self._store_instance_and_assert(
            test_instance,
            prediction_repository_test_subject,
            test_postgres_engine
        )
            
    async def test_upsert(
        self,
        prediction_repository_test_subject: PredictionRepository,
        test_postgres_engine: AsyncEngine
    ):
        """_summary_
        Creates 2 instances with indentical priamry keys. 
        Store and verify that first instance with database record.
        Then, store the second instance. Database record extracted using
        the same primary keys should return the new instance instead of 
        the old. 
        """
        original_instance = MatchPredictionTableFactory.build(
            match_id = 9999,
            predictor_name = 'regression_model'
        )
        
        updated_instance = MatchPredictionTableFactory.build(
            match_id = 9999,
            predictor_name = 'regression_model'
        )
        
        await self._store_instance_and_assert(
            original_instance,
            prediction_repository_test_subject,
            test_postgres_engine
        )
        
        # test that updated instance is inserted and replaces the original_instance
        await self._store_instance_and_assert(
            updated_instance,
            prediction_repository_test_subject,
            test_postgres_engine
        )
        

    async def _store_instance_and_assert(
        self,
        input_instance: MatchPredictionTable,
        prediction_repository_test_subject: PredictionRepository,
        test_postgres_engine: AsyncEngine
    ):
        """_summary_

        Args:
            input_instance (MatchPredictionTable): table instance to store
            prediction_repository_test_subject (PredictionRepository): repository test subject
            test_postgres_engine (AsyncEngine): test engine
            
        Stores input_instance, verify that record exist in database and retrieve it.
        Then, compared retrieved instance with stored instance. They are expected to be the same
        """
        # Arrange
        match_id = input_instance.match_id
        predictor_name = input_instance.predictor_name
        
        # Act
        await prediction_repository_test_subject.store_match_prediction(input_instance)
        ## fetch from database 
        actual_instance = await self._fetch_instance(test_postgres_engine, match_id, predictor_name)
        
         # Assert
        assert actual_instance is not None, f"Missing match after insert, got {actual_instance}"
        
        if actual_instance:
            self._assert_equal(input_instance, actual_instance)
    
    async def _fetch_instance(
        self, 
        test_postgres_engine: AsyncEngine,
        match_id: int,
        predictor_name: str
    ) -> MatchPredictionTable:
        
        async with AsyncSession(test_postgres_engine) as session:
            stmt = select(MatchPredictionTable).where(
                MatchPredictionTable.match_id == match_id,
                MatchPredictionTable.predictor_name == predictor_name
            )
            
            res = await session.execute(stmt)
            output_instance = res.scalars().one()
            
            return output_instance
    
    def _assert_equal(self, expected_instance: MatchPredictionTable, actual_instance: MatchPredictionTable):
        for field in MatchPredictionTable.model_fields.keys():
            expected_attr = getattr(expected_instance, field)
            actual_attr = getattr(actual_instance, field)
            
            assert expected_attr == actual_attr, (
                f"values mismatch for field {field} "
                f"expected {expected_attr}, got {actual_attr}"
            )
            

