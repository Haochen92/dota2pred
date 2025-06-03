import pytest
import pytest_asyncio

# Postgresql Imports
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from sqlmodel import SQLModel
from dota_oracle import models

# Redis Imports
from testcontainers.redis import RedisContainer
from testcontainers.postgres import PostgresContainer
import redis.asyncio as aioredis

# Services import
from dota_oracle.live_pipeline.redis_service import RedisService


from dota_oracle.utils.set_logging import get_logger




logger = get_logger(__name__)


@pytest.fixture(scope='session')
def redis_container_instance():
    with RedisContainer("redis:7-alpine") as redis_c:
        logger.info(f"Redis container started on {redis_c.get_container_host_ip()}:{redis_c.get_exposed_port(6379)}")
        yield redis_c
        logger.info("Redis Container Stopped")
        

@pytest_asyncio.fixture(scope="function")
async def test_redis_client(redis_container_instance: RedisContainer):
    host = redis_container_instance.get_container_host_ip()
    port = redis_container_instance.get_exposed_port(6379)
    
    client = aioredis.Redis(host=host, port=int(port), decode_responses=True, auto_close_connection_pool=False)
    await client.ping() # Verify connection
    yield client
    await client.aclose()
    
    
@pytest_asyncio.fixture(scope="function")
async def redis_service_test_subject(redis_container_instance: RedisContainer):
    """
    Provides an instance of your RedisService configured to use the
    Testcontainer's Redis. This is the "subject under test".
    It's function-scoped to potentially reset service state or re-initialize,
    though your RedisService's _initialized flag handles re-initialization idempotency.
    """
    host = redis_container_instance.get_container_host_ip()
    port = redis_container_instance.get_exposed_port(6379)

    # Create a NEW client instance specifically for the RedisService
    # Note: decode_responses=True should match what your RedisService expects
    # or how it handles data. Your RedisClientFactory uses decode_responses=True.
    service_redis_client = aioredis.Redis(host=host, port=int(port), decode_responses=True, auto_close_connection_pool=False)

    # Instantiate your service with this dedicated client
    service = RedisService(redis_client=service_redis_client)
    # We don't call service.initialize() here; tests will do that explicitly.
    yield service
    # Clean up the client used by the service
    await service_redis_client.aclose()
    

@pytest.fixture(scope='session')
def postgres_container_instance():
    with PostgresContainer("postgres:14-alpine") as postgres_c:
        logger.info(f"Redis container started on {postgres_c.get_container_host_ip()}:{postgres_c.get_exposed_port(5432)}")
        yield postgres_c
        logger.info("Redis Container Stopped")
        

@pytest_asyncio.fixture(scope="session")
async def test_postgres_engine(postgres_container_instance: PostgresContainer):
    
    # construct url directly for async engine
    host = postgres_container_instance.get_container_host_ip()
    port = postgres_container_instance.get_exposed_port(5432)
    user = postgres_container_instance.username
    password = postgres_container_instance.password
    dbname = postgres_container_instance.dbname

    async_db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}"
    engine = create_async_engine(async_db_url)
    logger.info(f"Test DB engine created for: {async_db_url}")
    yield engine
    logger.info("Disposing Test DB engine.")
    await engine.dispose()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_db_tables(test_postgres_engine: AsyncEngine):
    """
    Connects to the test DB and creates all tables defined in SQLModel.metadata.
    Runs once per session.
    """
    app_metadata_to_create = SQLModel.metadata
    
    async with test_postgres_engine.begin() as conn:
        logger.info("Dropping existing tables for a clean state")
        await conn.run_sync(SQLModel.metadata.drop_all)
        logger.info("Creating all tables in test database")
        await conn.run_sync(app_metadata_to_create.create_all)
        
    logger.info("Database tables created in test PostgreSQL container.")


@pytest_asyncio.fixture(scope="function")
async def db_session(test_postgres_engine):
    async with test_postgres_engine.connect() as connection: # Get dedicated connection
        async with connection.begin() as conn_transaction: # Start DB transaction
            LocalSession = async_sessionmaker(
                bind=connection, 
                class_=AsyncSession, 
                expire_on_commit=False
            )
            
            async with LocalSession() as session:
                yield session
                
            await conn_transaction.rollback()
            
            
    