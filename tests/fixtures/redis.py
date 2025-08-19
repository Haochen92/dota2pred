"""
Redis-related fixtures for tests.
"""

import pytest
import pytest_asyncio
from testcontainers.redis import RedisContainer
import redis.asyncio as aioredis
from unittest.mock import AsyncMock
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


# ========================
# Mock Fixtures
# ========================


@pytest.fixture
def mock_redis_client() -> aioredis.Redis:
    mock = AsyncMock(spec=aioredis.Redis)
    # Manually override methods that return coroutines in redis-py
    mock.publish = AsyncMock()
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    mock.delete = AsyncMock()
    mock.exists = AsyncMock()
    mock.expire = AsyncMock()
    mock.ttl = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.get_message = AsyncMock()
    # Add other async methods as needed for your use cases
    return mock
