import pytest

from dota_oracle_common.repositories.prediction_repository import PredictionRepository

from ..base_test_repository import BaseTestRepository
from .conftest import PredictorFetcherClass

from dota_oracle_common.utils.set_logging import get_logger


logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session')


class TestStoreMatchPrediction:
    
    async def test_successful_insert(
        self,
        prediction_repository_test_subject: PredictionRepository,
        test_repository: BaseTestRepository,
        prediction_db_fetcher: PredictorFetcherClass,
        seed_prediction_data,
        match_prediction_table_factory,
    ):
        # Arrange
        test_instance = match_prediction_table_factory.build(
            match_id = 1004, # new prediction data
            predictor_name = 'random_model' # primary key
        )
        await prediction_repository_test_subject.store_match_prediction(test_instance)
        
        instance = await prediction_db_fetcher.fetch_prediction_data(
            match_id=1004,
            predictor_name='random_model'
        )
        
        assert instance is not None,  f"Expected 1 records, got {instance}"
        
        test_repository._assert_equal(test_instance, instance, "upsert 1 record successfully")
        
        
        
            
    async def test_successful_update(
        self,
        prediction_repository_test_subject: PredictionRepository,
        test_repository: BaseTestRepository,
        prediction_db_fetcher: PredictorFetcherClass,
        seed_prediction_data,
        match_prediction_table_factory,
    ):
        # Arrange
        original_instance = match_prediction_table_factory.build(match_id=1005, predictor_name='model_1')
        new_instance = match_prediction_table_factory.build(match_id=1005, predictor_name='model_1')
        
        # Act
        await prediction_repository_test_subject.store_match_prediction(original_instance)
        
        original_res = await prediction_db_fetcher.fetch_prediction_data(
            match_id=1005,
            predictor_name='model_1'
        )
        
        # Assert
        assert original_res is not None 
        
        test_repository._assert_equal(original_instance, original_res, "original data insert")
        
        
        await prediction_repository_test_subject.store_match_prediction(new_instance)
        
        new_res = await prediction_db_fetcher.fetch_prediction_data(
            match_id=1005,
            predictor_name='model_1'
        )
        
        # Assert
        assert new_res is not None
        test_repository._assert_equal(new_instance, new_res, "original data insert")
