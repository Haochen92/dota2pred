import pytest
from dota_oracle.data_repository.schemas import MatchPredictionTable
from dota_oracle.data_repository.prediction_repository import PredictionRepository

from typing import List

from dota_oracle.utils.set_logging import get_logger

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session')


class TestMixinHelpers:
    """Shared helper methods for all test classes"""
    
    def _assert_predictions_equal(
        self, 
        expected: MatchPredictionTable, 
        actual: MatchPredictionTable
    ):
        """Assert that two prediction instances are equal"""
        for field in MatchPredictionTable.model_fields.keys():
            expected_attr = getattr(expected, field)
            actual_attr = getattr(actual, field)
            
            assert expected_attr == actual_attr, (
                f"values mismatch for field {field}: "
                f"expected {expected_attr}, got {actual_attr}"
            )
    
    def _assert_prediction_lists_equal(
        self, 
        expected_list: List[MatchPredictionTable], 
        actual_list: List[MatchPredictionTable]
    ):
        """Assert that two lists of predictions contain the same elements"""
        assert len(expected_list) == len(actual_list), (
            f"List length mismatch: expected {len(expected_list)}, got {len(actual_list)}"
        )
        
        # Sort both lists by match_id and predictor_name for consistent comparison
        expected_sorted = sorted(
            expected_list, 
            key=lambda x: (x.match_id, x.predictor_name)
        )
        actual_sorted = sorted(
            actual_list, 
            key=lambda x: (x.match_id, x.predictor_name)
        )
        
        for expected, actual in zip(expected_sorted, actual_sorted):
            self._assert_predictions_equal(expected, actual)


class TestGetSpecificPredictionByModelName(TestMixinHelpers):
    """Test get_specific_prediction_by_model_name method"""
    
    async def test_found_existing_prediction(
        self,
        prediction_repository_test_subject: PredictionRepository,
        seed_prediction_data: List[MatchPredictionTable]
    ):
        """Test retrieving an existing prediction by match_id and predictor_name"""
        # Arrange
        expected_prediction = seed_prediction_data[0]  # match_id=1001, predictor_name='random_forest'
        
        # Act
        result = await prediction_repository_test_subject.get_specific_prediction_by_model_name(
            match_id=expected_prediction.match_id,
            predictor_name=expected_prediction.predictor_name
        )
        
        # Assert
        assert result is not None
        self._assert_predictions_equal(expected_prediction, result)
    
    async def test_not_found_nonexistent_match_id(
        self,
        prediction_repository_test_subject: PredictionRepository,
        seed_prediction_data: List[MatchPredictionTable]
    ):
        """Test retrieving prediction with non-existent match_id"""
        # Act
        result = await prediction_repository_test_subject.get_specific_prediction_by_model_name(
            match_id=99999,  # Non-existent match_id
            predictor_name='random_forest'
        )
        
        # Assert
        assert result is None
    
    async def test_not_found_nonexistent_predictor_name(
        self,
        prediction_repository_test_subject: PredictionRepository,
        seed_prediction_data: List[MatchPredictionTable]
    ):
        """Test retrieving prediction with non-existent predictor_name"""
        # Act
        result = await prediction_repository_test_subject.get_specific_prediction_by_model_name(
            match_id=1001,
            predictor_name='nonexistent_model'
        )
        
        # Assert
        assert result is None
    
    async def test_not_found_valid_match_wrong_predictor(
        self,
        prediction_repository_test_subject: PredictionRepository,
        seed_prediction_data: List[MatchPredictionTable]
    ):
        """Test retrieving prediction with valid match_id but wrong predictor_name"""
        # Act - match 1002 only has random_forest, not xg_boost
        result = await prediction_repository_test_subject.get_specific_prediction_by_model_name(
            match_id=1002,
            predictor_name='xg_boost'
        )
        
        # Assert
        assert result is None


class TestGetPredictionsForMatchAllModels(TestMixinHelpers):
    """Test get_predictions_for_match_all_models method"""
    
    async def test_match_with_multiple_predictions(
        self,
        prediction_repository_test_subject: PredictionRepository,
        seed_prediction_data: List[MatchPredictionTable]
    ):
        """Test retrieving all predictions for match with multiple models"""
        # Arrange - match 1001 has 2 predictions
        expected_predictions = [p for p in seed_prediction_data if p.match_id == 1001]
        
        # Act
        result = await prediction_repository_test_subject.get_predictions_for_match_all_models(
            match_id=1001
        )
        
        # Assert
        assert len(result) == 2
        self._assert_prediction_lists_equal(expected_predictions, result)
    
    async def test_match_with_single_prediction(
        self,
        prediction_repository_test_subject: PredictionRepository,
        seed_prediction_data: List[MatchPredictionTable]
    ):
        """Test retrieving all predictions for match with single model"""
        # Arrange - match 1002 has 1 prediction
        expected_predictions = [p for p in seed_prediction_data if p.match_id == 1002]
        
        # Act
        result = await prediction_repository_test_subject.get_predictions_for_match_all_models(
            match_id=1002
        )
        
        # Assert
        assert len(result) == 1
        self._assert_prediction_lists_equal(expected_predictions, result)
    
    async def test_nonexistent_match_returns_empty_list(
        self,
        prediction_repository_test_subject: PredictionRepository,
        seed_prediction_data: List[MatchPredictionTable]
    ):
        """Test retrieving predictions for non-existent match returns empty list"""
        # Act
        result = await prediction_repository_test_subject.get_predictions_for_match_all_models(
            match_id=99999
        )
        
        # Assert
        assert result == []


class TestGetAllMatchPredictions(TestMixinHelpers):
    """Test get_all_match_predictions method"""
    
    async def test_returns_all_seeded_predictions(
        self,
        prediction_repository_test_subject: PredictionRepository,
        seed_prediction_data: List[MatchPredictionTable]
    ):
        """Test retrieving all predictions returns all seeded data"""
        # Act
        result = await prediction_repository_test_subject.get_all_match_predictions()
        
        # Assert
        assert len(result) == len(seed_prediction_data)
        self._assert_prediction_lists_equal(seed_prediction_data, result)
    
    async def test_empty_table_returns_empty_list(
        self,
        prediction_repository_test_subject: PredictionRepository
    ):
        """Test retrieving all predictions from empty table returns empty list"""
        # Note: This test doesn't use seed_prediction_data fixture, 
        # so table should be empty due to setup_and_clear_table fixture
        
        # Act
        result = await prediction_repository_test_subject.get_all_match_predictions()
        
        # Assert
        assert result == []


class TestGetPredictionsByPredictor(TestMixinHelpers):
    """Test get_predictions_by_predictor method"""
    
    async def test_predictor_with_multiple_predictions(
        self,
        prediction_repository_test_subject: PredictionRepository,
        seed_prediction_data: List[MatchPredictionTable]
    ):
        """Test retrieving predictions for predictor with multiple matches"""
        # Arrange - random_forest has 3 predictions
        expected_predictions = [p for p in seed_prediction_data if p.predictor_name == 'random_forest']
        
        # Act
        result = await prediction_repository_test_subject.get_predictions_by_predictor(
            predictor_name='random_forest'
        )
        
        # Assert
        assert len(result) == 3
        self._assert_prediction_lists_equal(expected_predictions, result)
    
    async def test_predictor_with_single_prediction(
        self,
        prediction_repository_test_subject: PredictionRepository,
        seed_prediction_data: List[MatchPredictionTable]
    ):
        """Test retrieving predictions for predictor with single match"""
        # Arrange - xg_boost has 1 prediction
        expected_predictions = [p for p in seed_prediction_data if p.predictor_name == 'xg_boost']
        
        # Act
        result = await prediction_repository_test_subject.get_predictions_by_predictor(
            predictor_name='xg_boost'
        )
        
        # Assert
        assert len(result) == 1
        self._assert_prediction_lists_equal(expected_predictions, result)
    
    async def test_nonexistent_predictor_returns_empty_list(
        self,
        prediction_repository_test_subject: PredictionRepository,
        seed_prediction_data: List[MatchPredictionTable]
    ):
        """Test retrieving predictions for non-existent predictor returns empty list"""
        # Act
        result = await prediction_repository_test_subject.get_predictions_by_predictor(
            predictor_name='nonexistent_predictor'
        )
        
        # Assert
        assert result == []