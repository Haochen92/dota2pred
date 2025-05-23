import pytest
import pytest_asyncio
import asyncio

from testcontainers.redis import RedisContainer
import redis.asyncio as aioredis

from dota_oracle.utils.set_logging import get_logger

from dota_oracle.live_pipeline.redis_service import RedisService


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