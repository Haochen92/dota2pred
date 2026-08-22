from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from dota_oracle_common.postgresql import database_session_factory_resource
from dota_oracle_common.redis_component.redis_client_factory import redis_client_resource
from dota_oracle_pipeline.data_extraction.api_clients.aiohttp_client import aiohttp_session_provider


pytestmark = pytest.mark.asyncio


async def test_database_resource_yields_factory_and_closes_engine():
    manager = MagicMock()
    manager.session_factory = MagicMock()
    manager.close_engine = AsyncMock()

    with patch("dota_oracle_common.postgresql.DatabaseManager", return_value=manager):
        async with database_session_factory_resource(database_url="postgresql+asyncpg://test") as factory:
            assert factory is manager.session_factory

    manager.close_engine.assert_awaited_once()


async def test_redis_resource_yields_client_and_closes_connection():
    connection = MagicMock()
    connection.client = MagicMock()
    connection.close = AsyncMock()

    with patch(
        "dota_oracle_common.redis_component.redis_client_factory.RedisConnection",
        return_value=connection,
    ):
        async with redis_client_resource(redis_url="redis://test") as client:
            assert client is connection.client

    connection.close.assert_awaited_once()


async def test_aiohttp_resource_closes_session():
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    with patch(
        "dota_oracle_pipeline.data_extraction.api_clients.aiohttp_client.aiohttp.ClientSession",
        return_value=session,
    ):
        async with aiohttp_session_provider() as yielded:
            assert yielded is session

    session.__aexit__.assert_awaited_once()
