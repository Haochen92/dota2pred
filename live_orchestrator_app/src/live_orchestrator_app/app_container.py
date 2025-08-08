# Prefect Orchestrator
from prefect import flow

import asyncio

from dependency_injector import providers, containers

# Redis client
from dota_oracle_common.redis_component.redis_client_factory import RedisClientFactory

# database
from dota_oracle_common.postgresql import DatabaseManager

# --- Feature Engineering Components ---
from dota_oracle_pipeline.feature_engineering.team_features_creator import TeamFeatureCreator
from dota_oracle_pipeline.feature_engineering.player_hero_features_creator import PlayerHeroFeaturesCreator

# --- Inference Components ---
from live_orchestrator_app.services.model_inference_service import ModelInferenceService

# --- Pipeline Services (Business Logic Wrappers) ---
from .redis_services.redis_service import RedisService
from .services.feature_engineering_service import FeatureEngineeringService
from .services.history_update_service import HistoryUpdateService
from .services.match_prediction_service import MatchPredictionService
from .services.feature_preparation_service import FeaturePreparationService
from .services.stale_match_service import StaleMatchService

# --- Pipeline Data Providers ---
from .data_fetching.new_match_data_provider import NewMatchDataProvider
from .feature_engineering.feature_engineering_data_provider import FeatureEngineeringDataProvider
from .prediction.prediction_data_provider import PredictionDataProvider
from .completion.completion_data_provider import CompletionDataProvider

# --- Pipeline Event Processors ---
from .data_fetching.new_match_event_processor import NewMatchEventProcessor
from .feature_engineering.feature_engineering_processor import FeatureEngineeringEventProcessor
from .prediction.prediction_event_processor import PredictionEventProcessor
from .completion.completion_event_processor import CompletionEventProcessor

# --- Orchestrators (Workflow Controllers) ---
from .data_fetching.new_match_orchestrator import NewMatchOrchestrator
from .feature_engineering.feature_engineering_orchestrator import FeatureEngineeringOrchestrator
from .prediction.prediction_orchestrator import PredictionOrchestrator
from .completion.completion_orchestrator import CompletionOrchestrator

# --- Root Application ---
from .app import MatchPipelineOrchestrator

from dota_oracle_common.utils import get_logger

logger = get_logger(__name__)


class AppContainer(containers.DeclarativeContainer):
    """
    Dependency Injection container for the application components.
    Follows a bottom-up definition:
    Clients -> Components -> Services -> Data Providers/ Event Processors -> Orchestrators -> Root
    """

    # --- Configuration ---
    # config = providers.Configuration() # Todo

    # --- Clients ---
    redis_async_pool = providers.Resource(RedisClientFactory.create_instance)
    db_session_factory = providers.Resource(DatabaseManager.get_session_factory)

    # --- Feature Engineering Components ---
    team_feature_creator = providers.Factory(TeamFeatureCreator)
    player_hero_features_creator = providers.Factory(PlayerHeroFeaturesCreator)

    # --- Inference Components ---
    model_inference_service = providers.Resource(ModelInferenceService.create)

    # --- Core Pipeline Services ---
    feature_preparation_service = providers.Factory(
        FeaturePreparationService, model_inference_service=model_inference_service
    )

    redis_service = providers.Resource(RedisService.create, redis_client=redis_async_pool)

    feature_engineering_service = providers.Factory(
        FeatureEngineeringService,
        team_feature_creator=team_feature_creator,
        player_hero_feature_creator=player_hero_features_creator,
    )
    history_update_service = providers.Factory(HistoryUpdateService)

    match_prediction_service = providers.Factory(
        MatchPredictionService,
        features_preparation_service=feature_preparation_service,
        model_inference_service=model_inference_service,
    )

    stale_match_service = providers.Factory(StaleMatchService, redis_service=redis_service)

    # --- Data Providers ---
    new_match_data_provider = providers.Factory(NewMatchDataProvider, redis_service=redis_service)

    feature_engineering_data_provider = providers.Factory(FeatureEngineeringDataProvider, redis_service=redis_service)

    prediction_data_provider = providers.Factory(
        PredictionDataProvider,
        redis_service=redis_service,
    )

    completion_data_provider = providers.Factory(
        CompletionDataProvider, redis_service=redis_service, stale_match_service=stale_match_service
    )

    # --- Event Processors ---
    new_match_event_processor = providers.Factory(NewMatchEventProcessor, db_session_factory=db_session_factory)

    feature_engineering_event_processor = providers.Factory(
        FeatureEngineeringEventProcessor,
        db_session_factory=db_session_factory,
        feature_engineering_service=feature_engineering_service,
    )

    prediction_event_processor = providers.Factory(
        PredictionEventProcessor,
        db_session_factory=db_session_factory,
        feature_preparation_service=feature_preparation_service,
        match_prediction_service=match_prediction_service,
    )

    completion_event_processor = providers.Factory(
        CompletionEventProcessor, history_update_service=history_update_service, db_session_factory=db_session_factory
    )

    # --- Orchestrators ---
    new_match_orchestrator = providers.Factory(
        NewMatchOrchestrator,
        redis_service=redis_service,
        data_provider=new_match_data_provider,
        event_processor=new_match_event_processor,
    )
    feature_engineering_orchestrator = providers.Factory(
        FeatureEngineeringOrchestrator,
        redis_service=redis_service,
        event_processor=feature_engineering_event_processor,
        data_provider=feature_engineering_data_provider,
    )
    prediction_orchestrator = providers.Factory(
        PredictionOrchestrator,
        redis_service=redis_service,
        event_processor=prediction_event_processor,
        data_provider=prediction_data_provider,
    )
    completion_orchestrator = providers.Factory(
        CompletionOrchestrator,
        redis_service=redis_service,
        history_update_service=history_update_service,
        completion_data_provider=completion_data_provider,
        completion_event_processor=completion_event_processor,
    )

    # --- Root application ---
    app = providers.Factory(
        MatchPipelineOrchestrator,
        new_match_orchestrator=new_match_orchestrator,
        feature_engineering_orchestrator=feature_engineering_orchestrator,
        prediction_orchestrator=prediction_orchestrator,
        completion_orchestrator=completion_orchestrator,
    )


@flow(name="start live orchestrator")
async def start_application() -> None:
    """
    Main entry point for the application.
    Initializes the container and its resources, then run application cycle.
    """
    container = AppContainer()
    # todo: container.config.from_yaml('config.yml') # Load config if implemented

    try:
        # Initialize resources
        logger.debug("Initializing container resources...")
        await container.init_resources()  # type: ignore
        logger.info("Container resources initialized.")

        # Get the main app after resources are initialized
        application = await container.app()  # type: ignore

        logger.debug("Running pipeline cycle...")
        await application.run_cycle()

    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        raise
    finally:
        # Shutdown resources
        logger.debug("Shutting down container resources...")
        await container.shutdown_resources()  # type: ignore
        logger.info("Container resources shut down.")


if __name__ == "__main__":
    asyncio.run(start_application())
