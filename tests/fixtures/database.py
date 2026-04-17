"""
Database-related fixtures for tests.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession, async_sessionmaker
from unittest.mock import AsyncMock, MagicMock
from sqlmodel import SQLModel
from testcontainers.postgres import PostgresContainer
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.postgresql import DatabaseManager

logger = get_logger(__name__)


@pytest.fixture(scope="session")
def postgres_container_instance():
    with PostgresContainer("postgres:14-alpine") as postgres_c:
        logger.info(
            f"Postgres container started on {postgres_c.get_container_host_ip()}:{postgres_c.get_exposed_port(5432)}"
        )
        yield postgres_c
        logger.info("Postgres Container Stopped")


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
    async with test_postgres_engine.connect() as connection:
        async with connection.begin() as conn_transaction:
            LocalSession = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)

            async with LocalSession() as session:
                yield session

            await conn_transaction.rollback()


@pytest.fixture
def mock_async_session() -> AsyncSession:
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_async_engine() -> AsyncEngine:
    return AsyncMock(spec=AsyncEngine)


@pytest.fixture
def mock_db_session_factory(mock_async_session: AsyncSession) -> async_sessionmaker[AsyncSession]:
    factory = MagicMock(spec=async_sessionmaker)
    factory.return_value.__aenter__.return_value = mock_async_session
    factory.return_value.__aexit__.return_value = None
    return factory


@pytest.fixture
def mock_database_manager() -> DatabaseManager:
    """Mock DatabaseManager for scheduler tests."""
    return MagicMock(spec=DatabaseManager)


@pytest_asyncio.fixture(scope="function")
async def test_session_factory(test_postgres_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """
    Creates a real session factory for integration tests that connects to the test database.
    This mimics what DatabaseManager.get_session_factory() would return in production.
    """
    return async_sessionmaker(
        bind=test_postgres_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
