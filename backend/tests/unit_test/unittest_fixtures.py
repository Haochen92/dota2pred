"""
Essential test fixtures for Dota Oracle pipeline tests.
MVP version - includes all core pipeline component mocks.
"""

import pytest
from unittest.mock import AsyncMock

# Core ML Pipeline Imports
from dota_oracle.feature_engineering import (
    PlayerHeroFeaturesCreator, 
    TeamFeatureCreator, 
    HeroesFeatureCreator
)
from dota_oracle.inference import ModelInferenceService

# Repository imports
from dota_oracle.data_repository.heroes_repository import HeroesRepository
from dota_oracle.data_repository.features_repository import FeaturesRepository
from dota_oracle.data_repository.history_repository import HistoryRepository
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.data_repository.prediction_repository import PredictionRepository


# Pipeline Services Import
from dota_oracle.live_pipeline.services.feature_engineering_service import FeatureEngineeringService
from dota_oracle.live_pipeline.services.feature_preparation_service import FeaturePreparationService
from dota_oracle.live_pipeline.services.fetch_outcome_service import FetchOutcomeService
from dota_oracle.live_pipeline.services.history_update_service import HistoryUpdateService
from dota_oracle.live_pipeline.services.match_prediction_service import MatchPredictionService
from dota_oracle.live_pipeline.services.redis_service import RedisService

# Orchestrator specific imports
from dota_oracle.live_pipeline.completion.completion_data_provider import CompletionDataProvider
from dota_oracle.live_pipeline.completion.completion_event_processor import CompletionEventProcessor
from dota_oracle.live_pipeline.completion.completion_orchestrator import CompletionOrchestrator

from dota_oracle.live_pipeline.data_fetching.new_match_data_provider import NewMatchDataProvider
from dota_oracle.live_pipeline.data_fetching.new_match_event_processor import NewMatchEventProcessor
from dota_oracle.live_pipeline.data_fetching.new_match_orchestrator import NewMatchOrchestrator

from dota_oracle.live_pipeline.feature_engineering.feature_engineering_data_provider import FeatureEngineeringDataProvider
from dota_oracle.live_pipeline.feature_engineering.feature_engineering_orchestrator import FeatureEngineeringOrchestrator
from dota_oracle.live_pipeline.feature_engineering.feature_engineering_processor import FeatureEngineeringEventProcessor

from dota_oracle.live_pipeline.prediction.prediction_data_provider import PredictionDataProvider
from dota_oracle.live_pipeline.prediction.prediction_event_processor import PredictionEventProcessor
from dota_oracle.live_pipeline.prediction.prediction_orchestrator import PredictionOrchestrator

# Factories import
from ..factories.unit_test_factory import ModelMetaDataAPIResponseFactory, ModelPredictionAPIResponseFactory

# sqlalchemy imports
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine


# ================================
# INFRASTRUCTURE MOCKS
# ================================

@pytest.fixture
def mock_async_session() -> AsyncSession:
    return AsyncMock(spec=AsyncSession)


# ================================
# REPOSITORY MOCKS
# ================================

@pytest.fixture
def mock_match_repository() -> MatchRepository:
    return AsyncMock(spec=MatchRepository)


@pytest.fixture
def mock_features_repository() -> FeaturesRepository:
    return AsyncMock(spec=FeaturesRepository)


@pytest.fixture
def mock_heroes_repository() -> HeroesRepository:
    return AsyncMock(spec=HeroesRepository)


@pytest.fixture
def mock_history_repository() -> HistoryRepository:
    return AsyncMock(spec=HistoryRepository)


@pytest.fixture
def mock_prediction_repository() -> PredictionRepository:
    return AsyncMock(spec=PredictionRepository)


# ================================
# SERVICE MOCKS (ESSENTIAL!)
# ================================

@pytest.fixture
def mock_redis_service() -> RedisService:
    return AsyncMock(spec=RedisService)


@pytest.fixture
def mock_feature_engineering_service() -> FeatureEngineeringService:
    return AsyncMock(spec=FeatureEngineeringService)


@pytest.fixture
def mock_history_update_service() -> HistoryUpdateService:
    return AsyncMock(spec=HistoryUpdateService)


@pytest.fixture
def mock_match_prediction_service() -> MatchPredictionService:
    return AsyncMock(spec=MatchPredictionService)


@pytest.fixture
def mock_feature_preparation_service() -> FeaturePreparationService:
    return AsyncMock(spec=FeaturePreparationService)


@pytest.fixture
def mock_model_inference_service() -> ModelInferenceService:
    return AsyncMock(spec=ModelInferenceService)


@pytest.fixture
def mock_fetch_outcome_service() -> FetchOutcomeService:
    return AsyncMock(spec=FetchOutcomeService)


# ================================
# DATA PROVIDER MOCKS (ESSENTIAL!)
# ================================

@pytest.fixture
def mock_new_match_data_provider() -> NewMatchDataProvider:
    return AsyncMock(spec=NewMatchDataProvider)


@pytest.fixture
def mock_feature_engineering_data_provider() -> FeatureEngineeringDataProvider:
    return AsyncMock(spec=FeatureEngineeringDataProvider)


@pytest.fixture
def mock_prediction_data_provider() -> PredictionDataProvider:
    return AsyncMock(spec=PredictionDataProvider)


@pytest.fixture
def mock_completion_data_provider() -> CompletionDataProvider:
    return AsyncMock(spec=CompletionDataProvider)


# ================================
# EVENT PROCESSOR MOCKS (ESSENTIAL!)
# ================================

@pytest.fixture
def mock_new_match_event_processor() -> NewMatchEventProcessor:
    return AsyncMock(spec=NewMatchEventProcessor)


@pytest.fixture
def mock_feature_engineering_event_processor() -> FeatureEngineeringEventProcessor:
    return AsyncMock(spec=FeatureEngineeringEventProcessor)


@pytest.fixture
def mock_prediction_event_processor() -> PredictionEventProcessor:
    return AsyncMock(spec=PredictionEventProcessor)


@pytest.fixture
def mock_completion_event_processor() -> CompletionEventProcessor:
    return AsyncMock(spec=CompletionEventProcessor)


# ================================
# ORCHESTRATOR MOCKS (ESSENTIAL!)
# ================================

@pytest.fixture
def mock_new_match_orchestrator() -> NewMatchOrchestrator:
    return AsyncMock(spec=NewMatchOrchestrator)


@pytest.fixture
def mock_feature_engineering_orchestrator() -> FeatureEngineeringOrchestrator:
    return AsyncMock(spec=FeatureEngineeringOrchestrator)


@pytest.fixture
def mock_prediction_orchestrator() -> PredictionOrchestrator:
    return AsyncMock(spec=PredictionOrchestrator)


@pytest.fixture
def mock_completion_orchestrator() -> CompletionOrchestrator:
    return AsyncMock(spec=CompletionOrchestrator)


# ================================
# COMPONENT FIXTURES
# ================================

@pytest.fixture
def player_hero_features_creator() -> PlayerHeroFeaturesCreator:
    return PlayerHeroFeaturesCreator(max_history_length=20)


@pytest.fixture
def team_feature_creator() -> TeamFeatureCreator:
    return TeamFeatureCreator()


@pytest.fixture
def heroes_feature_creator() -> HeroesFeatureCreator:
    return HeroesFeatureCreator()


@pytest.fixture
def mock_async_engine() -> AsyncEngine:
    return AsyncMock(spec=AsyncEngine)


# ================================
# DATA PROVIDER COMPONENT FIXTURES
# ================================

@pytest.fixture
def new_match_data_provider(mock_redis_service: RedisService) -> NewMatchDataProvider:
    return NewMatchDataProvider(redis_service=mock_redis_service)


@pytest.fixture
def feature_engineering_data_provider(
    mock_redis_service: RedisService,
    mock_async_engine: AsyncEngine
) -> FeatureEngineeringDataProvider:
    return FeatureEngineeringDataProvider(
        redis_service=mock_redis_service,
        db_engine=mock_async_engine
    )


@pytest.fixture
def prediction_data_provider(mock_redis_service: RedisService) -> PredictionDataProvider:
    return PredictionDataProvider(redis_service=mock_redis_service)


# ================================
# EVENT PROCESSOR COMPONENT FIXTURES
# ================================

@pytest.fixture
def new_match_event_processor(mock_async_engine: AsyncEngine) -> NewMatchEventProcessor:
    return NewMatchEventProcessor(db_engine=mock_async_engine)

@pytest.fixture
def completion_event_processor(mock_history_update_service, mock_async_engine)-> CompletionEventProcessor:
    processor = CompletionEventProcessor(
        db_engine=mock_async_engine,
        history_update_service=mock_history_update_service
    )
    
    return processor

@pytest.fixture
def feature_engineering_event_processor(
    mock_feature_engineering_service: FeatureEngineeringService,
    mock_async_engine: AsyncEngine
) -> FeatureEngineeringEventProcessor:
    return FeatureEngineeringEventProcessor(
        feature_engineering_service=mock_feature_engineering_service,
        db_engine=mock_async_engine
    )


@pytest.fixture
def prediction_event_processor(
    mock_async_engine: AsyncEngine,
    mock_feature_preparation_service: FeaturePreparationService,
    mock_match_prediction_service: MatchPredictionService
) -> PredictionEventProcessor:
    return PredictionEventProcessor(
        db_engine=mock_async_engine,
        feature_preparation_service=mock_feature_preparation_service,
        match_prediction_service=mock_match_prediction_service
    )


# ================================
# ORCHESTRATOR COMPONENT FIXTURES
# ================================

@pytest.fixture
def new_match_orchestrator(
    new_match_data_provider: NewMatchDataProvider,
    new_match_event_processor: NewMatchEventProcessor,
    mock_redis_service: RedisService
) -> NewMatchOrchestrator:
    return NewMatchOrchestrator(
        data_provider=new_match_data_provider,
        event_processor=new_match_event_processor,
        redis_service=mock_redis_service
    )


@pytest.fixture
def feature_engineering_orchestrator(
    mock_redis_service: RedisService,
    feature_engineering_data_provider: FeatureEngineeringDataProvider,
    feature_engineering_event_processor: FeatureEngineeringEventProcessor
) -> FeatureEngineeringOrchestrator:
    return FeatureEngineeringOrchestrator(
        redis_service=mock_redis_service,
        data_provider=feature_engineering_data_provider,
        event_processor=feature_engineering_event_processor
    )


@pytest.fixture
def prediction_orchestrator(
    mock_redis_service: RedisService,
    prediction_data_provider: PredictionDataProvider,
    prediction_event_processor: PredictionEventProcessor
) -> PredictionOrchestrator:
    return PredictionOrchestrator(
        redis_service=mock_redis_service,
        data_provider=prediction_data_provider,
        event_processor=prediction_event_processor
    )


@pytest.fixture
def completion_orchestrator(
    mock_redis_service: RedisService,
    mock_history_update_service: HistoryUpdateService,
    mock_completion_data_provider: CompletionDataProvider,
    mock_completion_event_processor: CompletionEventProcessor
) -> CompletionOrchestrator:
    return CompletionOrchestrator(
        redis_service=mock_redis_service,
        history_update_service=mock_history_update_service,
        completion_data_provider=mock_completion_data_provider,
        completion_event_processor=mock_completion_event_processor
    )
    
    
# Services Mock
@pytest.fixture
def feature_preparation_service(mock_model_inference_service)-> FeaturePreparationService:
    mock_model_inference_service.model_metadata = ModelMetaDataAPIResponseFactory.build()
    
    return FeaturePreparationService(mock_model_inference_service)


@pytest.fixture
async def model_inference_service() -> ModelInferenceService:
    service = await ModelInferenceService.create()
    return service