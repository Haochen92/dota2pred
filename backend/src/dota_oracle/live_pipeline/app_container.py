import asyncio
from dependency_injector import providers, containers
from dependency_injector.wiring import inject, Provide

# Redis client 
from dota_oracle.redis_component.redis_client_factory import RedisClientFactory

# database
from dota_oracle.postgresql import DatabaseEngineFactory

# --- Low-level Repositories ---
from dota_oracle.data_repository.features_repository import FeaturesRepository
from dota_oracle.data_repository.heroes_repository import HeroesRepository
from dota_oracle.data_repository.history_repository import HistoryRepository
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.data_repository.prediction_repository import PredictionRepository

# --- Feature Engineering Components ---
from dota_oracle.feature_engineering.team_feature_processor import TeamFeatureProcessor
from dota_oracle.feature_engineering.player_hero_features_processor import PlayerHeroFeaturesProcessor

# --- Inference Components ---
from dota_oracle.live_pipeline.prediction.feature_preparation_service import FeaturePreparationService 
from dota_oracle.inference.model_inference import ModelInferenceService

# --- Pipeline Services (Business Logic Wrappers) ---
from .redis_service import RedisService 
from .feature_engineering.feature_engineering_service import FeatureEngineeringService 
from .completion.history_update_service import HistoryUpdateService 
from .prediction.match_prediction_service import MatchPredictionService

# --- Orchestrators (Workflow Controllers) ---
from .data_fetching.new_match_orchestrator import NewMatchOrchestrator
from .feature_engineering.feature_engineering_orchestrator import FeatureEngineeringOrchestrator 
from .prediction.prediction_orchestrator import PredictionOrchestrator          
from .completion.completion_orchestrator import CompletionOrchestrator         
from .match_pipeline_orchestrator import MatchPipelineOrchestrator   

from dota_oracle.utils import get_logger

logger = get_logger(__name__)

class AppContainer(containers.DeclarativeContainer):
    """
    Dependency Injection container for the application components.
    Follows a bottom-up definition: Clients -> Repositories -> Services -> Orchestrators
    """

    # --- Configuration ---
    # config = providers.Configuration() # Todo

    # --- Clients ---
    redis_async_pool = providers.Singleton(RedisClientFactory.create_instance, env='test')
    db_engine = providers.Singleton(DatabaseEngineFactory.get_engine, env='test') 

    # --- Repositories ---
    heroes_repository = providers.Factory(HeroesRepository, engine=db_engine)
    features_repository = providers.Factory(FeaturesRepository, engine=db_engine)
    history_repository = providers.Factory(HistoryRepository, engine=db_engine)
    match_repository = providers.Factory(MatchRepository, engine=db_engine)
    prediction_repository = providers.Factory(PredictionRepository, engine=db_engine)

    # --- Feature Engineering Components ---
    team_feature_processor = providers.Factory(TeamFeatureProcessor, history_repository=history_repository)
    player_hero_features_processor = providers.Factory(PlayerHeroFeaturesProcessor, history_repository=history_repository)

    # --- Inference Components ---
    model_inference_service = providers.Resource(
        ModelInferenceService.initialize_async_service
    )

    feature_preparation_service = providers.Factory(
        FeaturePreparationService,
        features_repository=features_repository,
        heroes_repository=heroes_repository,
        model_inference_service=model_inference_service  
    )

    # --- Core Pipeline Services ---
    redis_service = providers.Resource(
        RedisService.initialize,
        redis_client=redis_async_pool 
    )
    
    feature_engineering_service = providers.Factory(
        FeatureEngineeringService,
        team_feature_processor=team_feature_processor,
        player_hero_processor=player_hero_features_processor,
        features_repository=features_repository
    )
    history_update_service = providers.Factory(
        HistoryUpdateService,
        history_repository=history_repository
    )
    match_prediction_service = providers.Factory(
        MatchPredictionService,
        feature_preparation_service=feature_preparation_service,
        model_inference_service=model_inference_service,
        prediction_repository=prediction_repository
    )

    # --- Orchestrators ---
    new_match_orchestrator = providers.Factory(
        NewMatchOrchestrator,
        redis_service=redis_service,
        storage=match_repository,
        hero_repo=heroes_repository
    )
    feature_engineering_orchestrator = providers.Factory(
        FeatureEngineeringOrchestrator,
        match_repository=match_repository,
        redis_service=redis_service,
        feature_engineering_service=feature_engineering_service
    )
    prediction_orchestrator = providers.Factory(
        PredictionOrchestrator,
        redis_service=redis_service,
        feature_preparation_service=feature_preparation_service, 
        match_prediction_service=match_prediction_service      
    )
    completion_orchestrator = providers.Factory(
        CompletionOrchestrator, 
        redis_service=redis_service,
        history_update_service=history_update_service,
        match_repository=match_repository
    )

    # --- Top-Level Orchestrator ---
    match_pipeline_orchestrator = providers.Factory(
        MatchPipelineOrchestrator,
        new_match_orchestrator=new_match_orchestrator,
        feature_engineering_orchestrator=feature_engineering_orchestrator,
        prediction_orchestrator=prediction_orchestrator,
        completion_orchestrator=completion_orchestrator
    )

# to do: wrap in prefect task or CRON task
async def run_pipeline():
    container = AppContainer()
    # todo: container.config.from_yaml('config.yml') # Load config if implemented

    try:
        # Initialize resources 
        logger.debug("Initializing container resources...")
        await container.init_resources() # type: ignore
        logger.info("Container resources initialized.")

        # Get the top-level orchestrator after resources are initialized
        pipeline_orchestrator = container.match_pipeline_orchestrator()

        logger.debug("Running pipeline cycle...")
        await pipeline_orchestrator.run_cycle()

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
    finally:
        # Shutdown resources 
        logger.debug("Shutting down container resources...")
        await container.shutdown_resources() # type: ignore
        logger.info("Container resources shut down.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())