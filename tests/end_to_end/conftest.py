import pytest
import pytest_asyncio
import redis.asyncio as aioredis
from typing import AsyncGenerator, Dict, Generator

from httpx import AsyncClient
from fastapi import FastAPI
from testcontainers.compose import DockerCompose
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel

# --- Imports from your application code ---
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.repositories.heroes_repository import HeroesRepository
from dota_oracle_common.models.heroes.table import HeroDataTable
from dota_oracle_pipeline.data_extraction.fetch_hero_data import fetch_hero_data
from dota_oracle_pipeline.inference.model_inference_service import ModelInferenceService

# Live Orchestrator App imports (for live pipeline tests)
from live_orchestrator_app.app_container import AppContainer
from dependency_injector import providers

# API Service imports (for API service tests)
from api_service.inference.pub_inference import PubInferenceService
from api_service.streaming.redis_pubsub_service import RedisPubSubService
from api_service.inference.router import router as inference_router
from api_service.matches.router import router as matches_router
from api_service.streaming.router import router as streaming_router

logger = get_logger(__name__)


# =================================================================================
# LEVEL 1: DOCKER COMPOSE ENVIRONMENT SETUP (Session-Scoped)
# =================================================================================


@pytest.fixture(scope="session")
def e2e_environment() -> Generator[Dict[str, str], None, None]:
    """
    Manages the lifecycle of the Docker Compose environment for E2E tests.
    Starts all services, waits for healthchecks, yields connection details,
    and tears down the environment at the end of the test session.
    """
    compose = DockerCompose(context="./tests/end_to_end/", compose_file_name="docker-compose.test.yml")

    with compose:
        db_host = compose.get_service_host("db", 5432)
        db_port = compose.get_service_port("db", 5432)
        db_url = f"postgresql+asyncpg://test:test@{db_host}:{db_port}/test"

        redis_host = compose.get_service_host("redis", 6379)
        redis_port = compose.get_service_port("redis", 6379)
        redis_url = f"redis://{redis_host}:{redis_port}"

        inference_host = compose.get_service_host("bentoml", 3000)
        inference_port = compose.get_service_port("bentoml", 3000)
        inference_url = f"http://{inference_host}:{inference_port}"

        logger.info("All services in Docker Compose are healthy and ready.")

        yield {
            "db_url": db_url,
            "redis_url": redis_url,
            "inference_url": inference_url,
        }
    logger.info("E2E Docker Compose environment has been shut down.")


# =================================================================================
# LEVEL 2: TEST RESOURCE FIXTURES (Session-Scoped)
# =================================================================================


@pytest_asyncio.fixture(scope="session")
async def e2e_postgres_engine(e2e_environment: dict):
    """Provides a SQLAlchemy async engine connected to the test PostgreSQL container."""
    engine = create_async_engine(e2e_environment["db_url"])
    logger.info(f"Test DB engine created for: {e2e_environment['db_url']}")
    yield engine
    logger.info("Disposing Test DB engine.")
    await engine.dispose()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_e2e_db_tables(e2e_postgres_engine):
    """Ensures the test database schema is created once before any tests run."""
    async with e2e_postgres_engine.begin() as conn:
        logger.info("Dropping existing tables for a clean state")
        await conn.run_sync(SQLModel.metadata.drop_all)
        logger.info("Creating all tables in test database")
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Database tables created in test PostgreSQL container.")


@pytest_asyncio.fixture(scope="session")
async def e2e_redis_client(e2e_environment: dict):
    """Provides an async Redis client connected to the test Redis container."""
    client = aioredis.from_url(e2e_environment["redis_url"], decode_responses=True)
    await client.ping()
    yield client
    await client.connection_pool.disconnect()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_hero_data(e2e_postgres_engine):
    """Populates the test database with essential hero data from an external API."""
    try:
        logger.info("Fetching hero data from API...")
        hero_data_dict = await fetch_hero_data()
        logger.info(f"Fetched {len(hero_data_dict)} heroes from API")

        if not hero_data_dict:
            pytest.fail("Failed to fetch hero data, which is required for E2E tests.")

        heroes_to_insert = {hero_id: HeroDataTable(**data.model_dump()) for hero_id, data in hero_data_dict.items()}

        async with AsyncSession(e2e_postgres_engine) as session:
            heroes_repo = HeroesRepository(session)
            await heroes_repo.upsert_hero_data(heroes_to_insert)
            await session.commit()

            # Verify the data was stored and is accessible
            hero_map = await heroes_repo.get_hero_id_map()
            logger.info(f"Verification: Retrieved hero map with {len(hero_map)} heroes")

            # Check if our test hero IDs are present
            test_hero_ids = [1, 2, 3, 4, 5]  # Anti-Mage, Axe, Bane, Bloodseeker, Crystal Maiden
            for hero_id in test_hero_ids:
                if hero_id in hero_map:
                    logger.info(f"Verified hero {hero_id}: {hero_map[hero_id]}")
                else:
                    logger.warning(f"Test hero {hero_id} not found in hero map!")

        logger.info(f"Successfully populated database with {len(heroes_to_insert)} heroes using repository.")
        print(f"\nINFO: Populated database with {len(heroes_to_insert)} heroes.")
    except Exception as e:
        logger.error(f"Error setting up hero data: {e}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        pytest.skip(f"Could not fetch hero data to populate DB, skipping E2E tests: {e}")


@pytest_asyncio.fixture(scope="session")
async def http_client() -> AsyncGenerator[AsyncClient, None]:
    """Provides a shared httpx.AsyncClient for making external requests."""
    import httpx

    async with httpx.AsyncClient() as client:
        yield client


# =================================================================================
# MODULE-SCOPED CLEANUP FIXTURES (Auto-run per module for isolation)
# =================================================================================


@pytest_asyncio.fixture(scope="module", autouse=True)
async def clean_transactional_db_tables(e2e_postgres_engine):
    """
    Ensures each test module starts with a clean database for transactional data.
    This runs automatically before any test in a given file.
    It TRUNCATES all tables EXCEPT the static hero data table.
    """
    logger.info("Cleaning transactional DB tables for new module...")
    tables_to_clean = [
        table
        for table in reversed(SQLModel.metadata.sorted_tables)
        if table.name != "herodatatable"  # IMPORTANT: Exclude static data
    ]
    from sqlalchemy import text

    async with e2e_postgres_engine.connect() as conn:
        async with conn.begin():
            for table in tables_to_clean:
                await conn.execute(text(f"TRUNCATE TABLE {table.name} RESTART IDENTITY CASCADE;"))
                logger.debug(f"Truncated table: {table.name}")

    logger.info(f"Cleaned {len(tables_to_clean)} transactional tables, preserved hero data")
    yield
    # No teardown needed here, as the next module will run this setup again.


@pytest_asyncio.fixture(scope="module", autouse=True)
async def clean_redis_module(e2e_redis_client: aioredis.Redis):
    """
    Ensures each test module starts with a clean Redis instance.
    This runs automatically before any test in a given file.
    """
    logger.info("Cleaning Redis for new module...")
    await e2e_redis_client.flushdb()
    logger.info("Redis cleaned - all keys removed for module isolation")
    yield


# =================================================================================
# LEVEL 3: FULL STACK API SERVICE TEST CLIENT (Session-Scoped)
# =================================================================================


@pytest_asyncio.fixture(scope="session")
async def full_stack_client(
    e2e_postgres_engine, e2e_redis_client, e2e_environment, http_client
) -> AsyncGenerator[AsyncClient, None]:
    """
    Provides a fully configured test client for the API service application.

    This fixture creates a new FastAPI app instance for testing, bypassing the
    production lifespan/startup logic. It manually populates `app.state` with
    dependencies connected to the live test infrastructure (Docker containers).
    """
    test_app = FastAPI(title="E2E API Service Test App")

    # --- Manually populate app.state with our test resources ---
    logger.info("Configuring E2E API service test application state...")

    # 1. Database
    test_session_factory = async_sessionmaker(bind=e2e_postgres_engine, class_=AsyncSession, expire_on_commit=False)
    test_app.state.db_session_factory = test_session_factory

    # 2. Redis
    test_app.state.redis_client = e2e_redis_client
    test_app.state.pubsub_service = RedisPubSubService(redis_client=e2e_redis_client)

    # 3. HTTP Client
    test_app.state.http_client = http_client

    # 4. Hero Map (from test database)
    async with test_session_factory() as session:
        hero_repo = HeroesRepository(session)
        hero_map = await hero_repo.get_hero_id_map()
        test_app.state.hero_map = hero_map

    # 5. Inference Service Stack (connected to test BentoML container)
    inference_base_url = e2e_environment["inference_url"]
    public_metadata_url = f"{inference_base_url}/metadata/public"
    public_prediction_url = f"{inference_base_url}/predict/public"

    model_metadata = await ModelInferenceService.fetch_model_metadata(
        http_client=http_client, metadata_url=public_metadata_url
    )

    model_inference_service = ModelInferenceService(
        model_metadata=model_metadata, http_client=http_client, prediction_url=public_prediction_url
    )

    test_app.state.public_inference_service = PubInferenceService(
        model_inference_service=model_inference_service,
        db_session_factory=test_session_factory,
    )

    logger.info("E2E API service test application state configured successfully.")

    # --- Include the application routers ---
    test_app.include_router(inference_router)
    test_app.include_router(matches_router)
    test_app.include_router(streaming_router)

    # --- Yield the test client ---
    from httpx import ASGITransport

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://testserver") as client:
        yield client


# =================================================================================
# LEVEL 4: LIVE ORCHESTRATOR APP FIXTURES (Function-Scoped)
# =================================================================================


@pytest_asyncio.fixture(scope="function")
async def test_app_container(e2e_redis_client, e2e_postgres_engine) -> AppContainer:
    """Provides a configured AppContainer for live orchestrator app tests."""
    container = AppContainer()
    container.redis_async_pool.override(e2e_redis_client)

    # Create session factory from engine
    session_factory = async_sessionmaker(bind=e2e_postgres_engine, class_=AsyncSession, expire_on_commit=False)
    container.db_session_factory.override(session_factory)

    return container


@pytest_asyncio.fixture(scope="function")
async def configured_test_container(test_app_container, http_client, e2e_environment):
    """Provides a fully configured AppContainer with all dependencies for live pipeline tests."""
    container = test_app_container
    inference_base_url = e2e_environment["inference_url"]

    # Build the correct inference URLs for e2e testing
    pro_matches_metadata_url = f"{inference_base_url}/metadata/pro"
    pro_matches_inference_url = f"{inference_base_url}/predict/pro"

    # Configure model metadata for testing
    model_metadata = await ModelInferenceService.fetch_model_metadata(http_client, pro_matches_metadata_url)
    container.model_metadata.override(providers.Object(model_metadata))

    # Configure http client for testing
    container.http_client.override(providers.Object(http_client))

    await container.init_resources()

    # Override the model inference service with correct e2e URL
    container.model_inference_service.override(
        providers.Factory(
            ModelInferenceService,
            http_client=http_client,
            model_metadata=providers.Object(model_metadata),
            prediction_url=pro_matches_inference_url,
        )
    )

    # Configure hero map for testing (required for the stateful FeatureEncoder)
    async with container.db_session_factory()() as session:
        hero_repo = HeroesRepository(session=session)
        hero_map_data = await hero_repo.get_hero_id_map()
        container.hero_map.override(providers.Object(hero_map_data))

    return container
