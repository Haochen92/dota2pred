import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- Import applications from common folder ---
from dota_oracle_common.constants.endpoint_configs import service_url
from dota_oracle_common.http_client import http_client_provider
from dota_oracle_common.postgresql import DatabaseManager
from dota_oracle_common.redis_component.redis_client_factory import RedisClientFactory
from dota_oracle_common.repositories.heroes_repository import HeroesRepository
from dota_oracle_common.utils import get_logger

# Import routers from their respective modules
from .inference.router import router as inference_router
from .matches.router import router as matchtable_router
from .streaming.router import router as streaming_router

# Import services needed for initialization
from dota_oracle_pipeline.inference.model_inference_service import ModelInferenceService
from dota_oracle_pipeline.feature_transformation.feature_encoder import FeatureEncoder
from .inference.pub_inference import PubInferenceService
from .streaming.redis_pubsub_service import RedisPubSubService


logger = get_logger(__name__)


async def setup_dependencies(app: FastAPI):
    """Initializes and attaches all application-level resources to the app state."""
    logger.info("Initializing application dependencies...")

    # Initialize and store database session factory
    app.state.db_session_factory = DatabaseManager.get_session_factory()
    logger.info("Database session factory created.")

    # Initialize and store Redis client and PubSub service
    redis_client = RedisClientFactory.create_instance()
    app.state.redis_client = redis_client
    app.state.pubsub_service = RedisPubSubService(redis_client=redis_client)
    logger.info("Redis client and PubSub service created.")

    # Initialize the entire inference service stack
    # The HTTP client is managed by the lifespan context and stored on the app state
    http_client = app.state.http_client

    logger.info("Fetching model metadata...")
    model_metadata = await ModelInferenceService.fetch_model_metadata(
        http_client=http_client,
        metadata_url=service_url.PUBLIC_MATCHES_METADATA_URL,
    )
    logger.info(f"Metadata for model version {model_metadata.version} fetched.")

    inference_service = ModelInferenceService(
        model_metadata=model_metadata,
        http_client=http_client,
        prediction_url=service_url.PUBLIC_MATCHES_INFERENCE_URL,
    )

    logger.info("Inference services initialized and ready.")

    # Initialize hero_id_map
    async with app.state.db_session_factory() as session:
        hero_repository = HeroesRepository(session)
        hero_map = await hero_repository.get_hero_id_map()
        app.state.hero_map = hero_map

    logger.info(f"Hero map initialized with {len(app.state.hero_map)} heroes.")

    app.state.feature_encoder = FeatureEncoder(app.state.hero_map)
    # Create and store the final, top-level service that endpoints will use
    app.state.public_inference_service = PubInferenceService(
        model_inference_service=inference_service,
        feature_encoder=app.state.feature_encoder,
    )
    logger.info("Public inference service initialized and ready.")

    logger.info("All application dependencies initialized successfully.")


async def teardown_dependencies():
    """Gracefully closes all application-level resources."""
    logger.info("Closing application dependencies...")
    await DatabaseManager.close_engine()
    await RedisClientFactory.close_instance()
    logger.info("All resources closed.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application's startup and shutdown lifecycle."""
    async with http_client_provider() as client:
        app.state.http_client = client
        await setup_dependencies(app)
        logger.info("API Gateway startup complete.")
        yield
        await teardown_dependencies()
    logger.info("API Gateway shutdown complete.")


# --- Application Factory ---
def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""
    app = FastAPI(
        title="Dota Oracle API Gateway",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(inference_router, tags=["Inference"])
    app.include_router(matchtable_router, tags=["Matches"])
    app.include_router(streaming_router, tags=["Streaming"])

    return app


app = create_app()

if __name__ == "__main__":
    # For local development
    uvicorn.run("your_app.app:app", host="0.0.0.0", port=8000, reload=True)
