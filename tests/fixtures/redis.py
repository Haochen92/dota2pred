"""
Redis-related fixtures for tests.
"""

import pytest
import pytest_asyncio
from testcontainers.redis import RedisContainer
import redis.asyncio as aioredis
from live_orchestrator_app.redis_services.redis_service import RedisService
from dota_oracle_common.utils.set_logging import get_logger

logger = get_logger(__name__)


@pytest.fixture(scope="session")
def redis_container_instance():
    with RedisContainer("redis:7-alpine") as redis_c:
        logger.info(f"Redis container started on {redis_c.get_container_host_ip()}:{redis_c.get_exposed_port(6379)}")
        yield redis_c
        logger.info("Redis Container Stopped")


@pytest_asyncio.fixture(scope="function")
async def test_redis_client(redis_container_instance: RedisContainer):
    host = redis_container_instance.get_container_host_ip()
    port = redis_container_instance.get_exposed_port(6379)

    pool = aioredis.ConnectionPool(host=host, port=int(port), decode_responses=True)
    client = aioredis.Redis(connection_pool=pool)

    await client.ping()  # Verify connection
    yield client
    await pool.disconnect()


@pytest_asyncio.fixture(scope="function")
async def redis_service_test_subject(redis_container_instance: RedisContainer):
    """
    Provides an instance of your RedisService configured to use the
    Testcontainer's Redis. This is the "subject under test".
    """
    host = redis_container_instance.get_container_host_ip()
    port = redis_container_instance.get_exposed_port(6379)

    pool = aioredis.ConnectionPool(host=host, port=int(port), decode_responses=True)
    service_redis_client = aioredis.Redis(connection_pool=pool)

    # Instantiate your service with this dedicated client
    service = RedisService(redis_client=service_redis_client)

    # Initialize the service to create consumer groups
    await service.initialize_async_service()

    yield service
    # Clean up the client used by the service
    await pool.disconnect()


@pytest.fixture
def mock_redis_service() -> RedisService:
    from unittest.mock import AsyncMock

    return AsyncMock(spec=RedisService)
