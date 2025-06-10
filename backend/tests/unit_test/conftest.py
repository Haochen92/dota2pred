"""
Essential test fixtures for Dota Oracle pipeline tests.
MVP version - includes all core pipeline component mocks.
"""

import pytest
from unittest.mock import AsyncMock
import numpy as np

# Core imports
from dota_oracle.feature_engineering import (
    PlayerHeroFeaturesCreator, 
    TeamFeatureCreator, 
    HeroesFeatureCreator
)

# Factories import
from ..factories.unit_test_factory import ModelMetaDataAPIResponseFactory, ModelPredictionAPIResponseFactory

from sqlalchemy.ext.asyncio import AsyncSession

# ================================
# INFRASTRUCTURE MOCKS
# ================================

@pytest.fixture
def mock_async_session():
    session = AsyncMock(spec=AsyncSession)
    return session

@pytest.fixture
def mock_redis_client():
    client = AsyncMock()
    client.smembers.return_value = set()
    client.sadd.return_value = 1
    client.hset.return_value = 1
    client.xadd.return_value = "1234567890-0"
    client.xreadgroup.return_value = []
    client.xack.return_value = 1
    return client


# ================================
# REPOSITORY MOCKS
# ================================

@pytest.fixture
def mock_match_repository():
    repo = AsyncMock()
    repo.get_match_details.return_value = []
    repo.insert_match_details.return_value = None
    repo.insert_match_outcome.return_value = None
    return repo


@pytest.fixture
def mock_features_repository():
    repo = AsyncMock()
    repo.store_features.return_value = None
    return repo


@pytest.fixture
def mock_heroes_repository():
    repo = AsyncMock()
    repo.get_hero_id_map.return_value = {1: "hero1", 2: "hero2", 3: "hero3"}
    return repo


@pytest.fixture
def mock_history_repository():
    repo = AsyncMock()
    repo.get_player_hero_win_history.return_value = [True, False, True]
    repo.get_team_history.return_value = [True, True, False]
    repo.get_team_matchup_history.return_value = [True, False]
    repo.add_team_match_outcome.return_value = None
    repo.add_player_hero_match_outcome.return_value = None
    repo.add_team_matchup_outcome.return_value = None
    return repo


@pytest.fixture
def mock_prediction_repository():
    repo = AsyncMock()
    repo.store_match_prediction.return_value = None
    return repo


# ================================
# SERVICE MOCKS (ESSENTIAL!)
# ================================

@pytest.fixture
def mock_redis_service():
    from dota_oracle.live_pipeline.services.redis_service import RedisService
    service = AsyncMock(spec=RedisService)
    service.update_live_match_set_and_get_new.return_value = {12345}
    service.add_match_for_processing.return_value = True
    service.fetch_new_matches_for_feature_eng.return_value = {}
    service.advance_match_to_pending_prediction.return_value = True
    service.fetch_matches_pending_prediction.return_value = {}
    service.advance_match_to_pending_completion.return_value = True
    service.fetch_matches_pending_completion.return_value = {}
    service.mark_match_as_completed.return_value = True
    service.handle_processing_failure.return_value = None
    return service


@pytest.fixture
def mock_feature_engineering_service():
    from dota_oracle.live_pipeline.services.feature_engineering_service import FeatureEngineeringService
    service = AsyncMock(spec=FeatureEngineeringService)
    service.create_and_store_features.return_value = None
    return service


@pytest.fixture
def mock_history_update_service():
    from dota_oracle.live_pipeline.services.history_update_service import HistoryUpdateService
    service = AsyncMock(spec=HistoryUpdateService)
    service.update_histories.return_value = None
    return service


@pytest.fixture
def mock_match_prediction_service():
    from dota_oracle.live_pipeline.services.match_prediction_service import MatchPredictionService
    service = AsyncMock(spec=MatchPredictionService)
    service.predict_and_store.return_value = None
    return service


@pytest.fixture
def mock_feature_preparation_service():
    from dota_oracle.live_pipeline.services.feature_preparation_service import FeaturePreparationService
    service = AsyncMock(spec=FeaturePreparationService)
    service.prepare_features_for_inference.return_value = np.array([[0.1, 0.2, 0.3]])
    return service


@pytest.fixture
def mock_model_inference_service():
    from dota_oracle.inference.model_inference_service import ModelInferenceService
    service = AsyncMock(spec=ModelInferenceService)
    service.model_metadata = ModelMetaDataAPIResponseFactory.build()
    service.get_prediction.return_value = ModelPredictionAPIResponseFactory.build()
    service.get_model_metadata.return_value = ModelMetaDataAPIResponseFactory.build()
    return service


@pytest.fixture
def mock_fetch_outcome_service():
    from dota_oracle.live_pipeline.services.fetch_outcome_service import FetchOutcomeService
    service = AsyncMock(spec=FetchOutcomeService)
    service.fetch_outcomes_batch.return_value = {12345: True}
    return service


# ================================
# DATA PROVIDER MOCKS (ESSENTIAL!)
# ================================

@pytest.fixture
def mock_new_match_data_provider():
    from dota_oracle.live_pipeline.data_fetching.new_match_data_provider import NewMatchDataProvider
    provider = AsyncMock(spec=NewMatchDataProvider)
    provider.get_work_items.return_value = []
    return provider


@pytest.fixture
def mock_feature_engineering_data_provider():
    from dota_oracle.live_pipeline.feature_engineering.feature_engineering_data_provider import FeatureEngineeringDataProvider
    provider = AsyncMock(spec=FeatureEngineeringDataProvider)
    provider.get_work_items.return_value = []
    return provider


@pytest.fixture
def mock_prediction_data_provider():
    from dota_oracle.live_pipeline.prediction.prediction_data_provider import PredictionDataProvider
    provider = AsyncMock(spec=PredictionDataProvider)
    provider.get_work_items.return_value = []
    return provider


@pytest.fixture
def mock_completion_data_provider():
    from dota_oracle.live_pipeline.completion.completion_data_provider import CompletionDataProvider
    provider = AsyncMock(spec=CompletionDataProvider)
    provider.get_work_items.return_value = []
    return provider


# ================================
# EVENT PROCESSOR MOCKS (ESSENTIAL!)
# ================================

@pytest.fixture
def mock_new_match_event_processor():
    from dota_oracle.live_pipeline.data_fetching.new_match_event_processor import NewMatchEventProcessor
    processor = AsyncMock(spec=NewMatchEventProcessor)
    processor.process_event.return_value = None
    return processor


@pytest.fixture
def mock_feature_engineering_event_processor():
    from dota_oracle.live_pipeline.feature_engineering.feature_engineering_processor import FeatureEngineeringEventProcessor
    processor = AsyncMock(spec=FeatureEngineeringEventProcessor)
    processor.process_event.return_value = None
    return processor


@pytest.fixture
def mock_prediction_event_processor():
    from dota_oracle.live_pipeline.prediction.prediction_event_processor import PredictionEventProcessor
    processor = AsyncMock(spec=PredictionEventProcessor)
    processor.process_event.return_value = None
    return processor


@pytest.fixture
def mock_completion_event_processor():
    from dota_oracle.live_pipeline.completion.completion_event_processor import CompletionEventProcessor
    processor = AsyncMock(spec=CompletionEventProcessor)
    processor.process_events.return_value = None
    return processor


# ================================
# ORCHESTRATOR MOCKS (ESSENTIAL!)
# ================================

@pytest.fixture
def mock_new_match_orchestrator():
    from dota_oracle.live_pipeline.data_fetching.new_match_orchestrator import NewMatchOrchestrator
    orchestrator = AsyncMock(spec=NewMatchOrchestrator)
    orchestrator.run_new_match_cycle.return_value = 0
    return orchestrator


@pytest.fixture
def mock_feature_engineering_orchestrator():
    from dota_oracle.live_pipeline.feature_engineering.feature_engineering_orchestrator import FeatureEngineeringOrchestrator
    orchestrator = AsyncMock(spec=FeatureEngineeringOrchestrator)
    orchestrator.run_feature_engineering_cycle.return_value = 0
    return orchestrator


@pytest.fixture
def mock_prediction_orchestrator():
    from dota_oracle.live_pipeline.prediction.prediction_orchestrator import PredictionOrchestrator
    orchestrator = AsyncMock(spec=PredictionOrchestrator)
    orchestrator.run_prediction_cycle.return_value = 0
    return orchestrator


@pytest.fixture
def mock_completion_orchestrator():
    from dota_oracle.live_pipeline.completion.completion_orchestrator import CompletionOrchestrator
    orchestrator = AsyncMock(spec=CompletionOrchestrator)
    orchestrator.run_completion_cycle.return_value = 0
    return orchestrator


# ================================
# COMPONENT FIXTURES
# ================================

@pytest.fixture
def player_hero_features_creator():
    return PlayerHeroFeaturesCreator(max_history_length=20)


@pytest.fixture
def team_feature_creator():
    return TeamFeatureCreator()


@pytest.fixture
def heroes_feature_creator():
    return HeroesFeatureCreator()



# ================================
# UTILITIES
# ================================

@pytest.fixture
def mock_task_result_factory():
    """Factory for creating mock TaskResult objects."""
    class MockTaskResult:
        def __init__(self, key: str, result=None, exception=None):
            self.key = key
            self._result = result
            self._exception = exception
            
        def get_result(self):
            if self._exception:
                raise self._exception
            return self._result
        
    return MockTaskResult