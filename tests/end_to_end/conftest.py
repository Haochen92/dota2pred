import pytest
import pytest_asyncio
import logging
from testcontainers.compose import DockerCompose
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
import redis.asyncio as aioredis
from live_orchestrator_app.app_container import AppContainer
from dependency_injector import providers
from live_orchestrator_app.inference.model_inference_service import ModelInferenceService

logger = logging.getLogger(__name__)

@pytest.fixture(scope='package')
def e2e_environment():
    compose = DockerCompose(context='.', compose_file_name="docker-compose.test.yml")
    
    with compose:
        prediction_host = compose.get_service_host("bentoml", 3000)
        prediction_port = compose.get_service_port("bentoml", 3000)
        prediction_url = f"http://{prediction_host}:{prediction_port}"
        
        db_host = compose.get_service_host("db", 5432)
        db_port = compose.get_service_port("db", 5432)
        db_url = f"postgresql+asyncpg://test:test@{db_host}:{db_port}/test"
        
        redis_host = compose.get_service_host("redis", 6379)
        redis_port = compose.get_service_port("redis", 6379)
        redis_url = f"redis://{redis_host}:{redis_port}"
    
        # Wait for services health check
        logger.info(f"Waiting for BentoML service to be ready at {prediction_url}")
        compose.wait_for(f"{prediction_url}/readyz")
        logger.info("All services are ready")
        
        yield {
            "db_url": db_url,
            "redis_url": redis_url,
            "prediction_api_url": prediction_url,
        }
    logger.info("E2E environment has been shut down.")

@pytest_asyncio.fixture(scope='package')
async def e2e_postgres_engine(e2e_environment: dict):
    async_db_url = e2e_environment.get("db_url")
    if not async_db_url:
        raise ValueError("Missing async_db_url")
    
    engine = create_async_engine(async_db_url)
    logger.info(f"Test DB engine created for: {async_db_url}")
    
    yield engine
    
    logger.info("Disposing Test DB engine.")
    await engine.dispose()

@pytest_asyncio.fixture(scope="package", autouse=True)
async def create_e2e_db_tables(e2e_postgres_engine):
    app_metadata_to_create = SQLModel.metadata
    
    async with e2e_postgres_engine.begin() as conn:
        logger.info("Dropping existing tables for a clean state")
        await conn.run_sync(SQLModel.metadata.drop_all)
        logger.info("Creating all tables in test database")
        await conn.run_sync(app_metadata_to_create.create_all)
        
    logger.info("Database tables created in test PostgreSQL container.")
    

@pytest_asyncio.fixture(scope='package')
async def e2e_redis_client(e2e_environment: dict):
    client = aioredis.from_url(e2e_environment["redis_url"], decode_responses=True)
    await client.ping()
    yield client
    
    # Clean up
    await client.connection_pool.disconnect()


@pytest_asyncio.fixture(scope='function')
async def test_app_container(
    e2e_redis_client,
    e2e_postgres_engine,
    e2e_environment
)-> AppContainer:
    container = AppContainer()
    container.redis_async_pool.override(e2e_redis_client)
    container.db_engine.override(e2e_postgres_engine)
    
    # Override model inference service with correct URL
    prediction_url = e2e_environment["prediction_api_url"]
    container.model_inference_service.override(
        providers.Resource(ModelInferenceService.create, base_url=prediction_url)
    )
    
    return container


@pytest_asyncio.fixture(scope='function')
async def configured_test_container(test_app_container):
    container = test_app_container
    try:
        # 1. SETUP: Initialize resources before the test runs
        await container.init_resources()
        
        # 2. PROVIDE: Yield the ready-to-use container to the test
        yield container
        
    finally:
        # 3. TEARDOWN: Guarantee resources are shut down after the test
        await container.shutdown_resources()