# Prefect Orchestrator
from prefect import flow

import asyncio

from typing import Dict

from dependency_injector import providers, containers

# Redis client
from dota_oracle_common.redis_component.redis_client_factory import RedisClientFactory

# database
from dota_oracle_common.postgresql import DatabaseManager

# HTTPX client
from dota_oracle_common.http_client import http_client_provider

# Model metadata
from dota_oracle_common.models.inference.schema import ModelMetaDataAPIResponse

# Endpoint configurations
from dota_oracle_common.constants.endpoint_configs import service_url
from dota_oracle_common.constants.hyperparam_config import (
    HERO_FEATURES_HYPERPARAMS,
    TEAM_FEATURES_HYPERPARAMS,
    PLAYER_HERO_FEATURES_HYPERPARAMS,
)

# --- Feature Engineering Components ---
from dota_oracle_pipeline.feature_engineering.team_features_creator import TeamFeatureCreator
from dota_oracle_pipeline.feature_engineering.player_hero_features_creator import PlayerHeroFeaturesCreator
from dota_oracle_pipeline.feature_engineering.heroes_features_creator import HeroesFeatureCreator

# --- Inference Components ---
from dota_oracle_pipeline.inference.model_inference_service import ModelInferenceService

# --- Pipeline Services (Business Logic Wrappers) ---
from .redis_services.redis_service import RedisService
from .services.feature_engineering_service import FeatureEngineeringService
from .services.history_update_service import HistoryUpdateService
from .services.match_prediction_service import MatchPredictionService
from .services.feature_preparation_service import FeaturePreparationService
from .services.stale_match_service import StaleMatchService
from .services.notifications_service import NotificationService

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

# --- Hero Repository for fetching hero map ---
from dota_oracle_common.repositories.heroes_repository import HeroesRepository

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
    http_client = providers.Resource(http_client_provider)

    # --- Configuration Provider ---
    # This will hold the metadata object once we fetch it.
    model_metadata = providers.Singleton(ModelMetaDataAPIResponse)
    hero_map = providers.Singleton(Dict[int, str])

    # --- Feature Engineering Components ---
    hero_feature_creator = providers.Factory(
        HeroesFeatureCreator,
        prior_mean=HERO_FEATURES_HYPERPARAMS.prior_mean,
        prior_count=HERO_FEATURES_HYPERPARAMS.prior_count,
        half_life_days=HERO_FEATURES_HYPERPARAMS.half_life_days,
    )
    team_feature_creator = providers.Factory(
        TeamFeatureCreator,
        prior_mean=TEAM_FEATURES_HYPERPARAMS.prior_mean,
        prior_count=TEAM_FEATURES_HYPERPARAMS.prior_count,
        half_life_days=TEAM_FEATURES_HYPERPARAMS.half_life_days,
    )
    player_hero_features_creator = providers.Factory(
        PlayerHeroFeaturesCreator,
        player_prior_count=PLAYER_HERO_FEATURES_HYPERPARAMS.player_prior_count,
        player_half_life_days=PLAYER_HERO_FEATURES_HYPERPARAMS.player_half_life_days,
        hero_prior_mean=PLAYER_HERO_FEATURES_HYPERPARAMS.hero_prior_mean,
        hero_prior_count=PLAYER_HERO_FEATURES_HYPERPARAMS.hero_prior_count,
        hero_half_life_days=PLAYER_HERO_FEATURES_HYPERPARAMS.hero_half_life_days,
    )

    # --- Inference Components ---
    model_inference_service = providers.Factory(
        ModelInferenceService,
        http_client=http_client,
        model_metadata=model_metadata,
        prediction_url=service_url.PRO_MATCHES_INFERENCE_URL,
    )

    # --- Core Pipeline Services ---
    feature_preparation_service = providers.Factory(
        FeaturePreparationService,
        model_metadata=model_metadata,
    )

    redis_service = providers.Resource(RedisService.create, redis_client=redis_async_pool)

    feature_engineering_service = providers.Factory(
        FeatureEngineeringService,
        hero_feature_creator=hero_feature_creator,
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

    notification_service = providers.Factory(
        NotificationService, redis_service=redis_service, db_session_factory=db_session_factory, http_client=http_client
    )

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
        notification_service=notification_service,
    )


@flow(name="start live orchestrator", timeout_seconds=400)
async def start_application() -> None:
    """
    Main entry point. Initializes the container, fetches dynamic configuration,
    and runs the main application logic.
    """
    container = AppContainer()

    try:
        # 1. Initialize all basic resources (DB pools, HTTP clients, etc.)
        logger.info("Initializing container resources...")
        await container.init_resources()
        logger.info("Container resources initialized.")

        # Fetch Model Metadata
        http_client = await container.http_client()
        logger.info("Fetching model metadata...")
        metadata = await ModelInferenceService.fetch_model_metadata(http_client, service_url.PRO_MATCHES_METADATA_URL)
        container.model_metadata.override(providers.Object(metadata))
        logger.info(f"Model metadata configured for version: {metadata.version_metadata}")

        # Fetch Hero Map
        async with container.db_session_factory()() as session:
            logger.info("Fetching hero map from database...")
            hero_repo = HeroesRepository(session=session)
            hero_map_data = await hero_repo.get_hero_id_map()
            container.hero_map.override(providers.Object(hero_map_data))
        logger.info(f"Hero map configured with {len(hero_map_data)} heroes.")

        application = await container.app()

        logger.info("Running pipeline cycle...")
        # Ensure a single cycle cannot hang forever
        cycle_timeout_seconds = 300
        try:
            await asyncio.wait_for(application.run_cycle(), timeout=cycle_timeout_seconds)
        except asyncio.TimeoutError:
            logger.error(f"Pipeline cycle timed out after {cycle_timeout_seconds} seconds")
            # Re-raise so Prefect marks the flow as failed and frees concurrency
            raise

    except Exception as e:
        logger.error(f"Critical application failure: {e}", exc_info=True)
        raise
    finally:
        logger.info("Shutting down container resources...")
        await container.shutdown_resources()
        logger.info("Container resources shut down.")


if __name__ == "__main__":
    asyncio.run(start_application())
