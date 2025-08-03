import pytest
import pytest_asyncio
from dota_oracle_common.utils.set_logging import get_logger
from testcontainers.compose import DockerCompose
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
import redis.asyncio as aioredis
from live_orchestrator_app.app_container import AppContainer
from dota_oracle_pipeline.data_extraction.fetch_hero_data import fetch_hero_data
from dota_oracle_common.models.heroes.table import HeroDataTable

logger = get_logger(__name__)


@pytest.fixture(scope="package")
def e2e_environment():
    compose = DockerCompose(context="./tests/end_to_end/", compose_file_name="docker-compose.test.yml")

    with compose:

        db_host = compose.get_service_host("db", 5432)
        db_port = compose.get_service_port("db", 5432)
        db_url = f"postgresql+asyncpg://test:test@{db_host}:{db_port}/test"

        redis_host = compose.get_service_host("redis", 6379)
        redis_port = compose.get_service_port("redis", 6379)
        redis_url = f"redis://{redis_host}:{redis_port}"

        logger.info("All services are ready")

        yield {
            "db_url": db_url,
            "redis_url": redis_url,
        }
    logger.info("E2E environment has been shut down.")


@pytest_asyncio.fixture(scope="package")
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


@pytest_asyncio.fixture(scope="package")
async def e2e_redis_client(e2e_environment: dict):
    client = aioredis.from_url(e2e_environment["redis_url"], decode_responses=True)
    await client.ping()
    yield client

    # Clean up
    await client.connection_pool.disconnect()


@pytest_asyncio.fixture(scope="package", autouse=True)
async def setup_hero_data(e2e_postgres_engine):
    """Ensures the database is populated with hero data."""
    try:
        logger.info("Fetching hero data from API...")
        hero_data_dict = await fetch_hero_data()
        logger.info(f"Fetched {len(hero_data_dict)} heroes from API")

        if not hero_data_dict:
            logger.error("No heroes data fetched from API endpoint")
            return

        logger.info(f"Inserting {len(hero_data_dict)} heroes into database using HeroesRepository...")
        from sqlalchemy.ext.asyncio import AsyncSession
        from dota_oracle_common.repositories.heroes_repository import HeroesRepository

        # Convert HeroData instances to HeroDataTable instances with correct format
        heroes_table_dict = {hero_id: HeroDataTable(**data.model_dump()) for hero_id, data in hero_data_dict.items()}

        async with AsyncSession(e2e_postgres_engine) as session:
            heroes_repo = HeroesRepository(session)
            await heroes_repo.upsert_hero_data(heroes_table_dict)
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

        logger.info(f"Successfully populated database with {len(heroes_table_dict)} heroes using repository.")
        print(f"\nINFO: Populated database with {len(heroes_table_dict)} heroes.")
    except Exception as e:
        logger.error(f"Error setting up hero data: {e}")
        import traceback

        logger.error(f"Full traceback: {traceback.format_exc()}")
        pytest.skip(f"Could not fetch hero data to populate DB, skipping E2E tests: {e}")


@pytest_asyncio.fixture(scope="function")
async def test_app_container(e2e_redis_client, e2e_postgres_engine) -> AppContainer:
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

    container = AppContainer()
    container.redis_async_pool.override(e2e_redis_client)

    # Create session factory from engine
    session_factory = async_sessionmaker(bind=e2e_postgres_engine, class_=AsyncSession, expire_on_commit=False)
    container.db_session_factory.override(session_factory)

    return container


@pytest_asyncio.fixture(scope="function")
async def configured_test_container(test_app_container):
    container = test_app_container
    await container.init_resources()

    return container
