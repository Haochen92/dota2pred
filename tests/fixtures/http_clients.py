import pytest
from unittest.mock import AsyncMock
import httpx
from typing import AsyncGenerator
from httpx import AsyncClient


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Provides a reusable mock for the httpx.AsyncClient."""
    return AsyncMock(spec=AsyncClient)


@pytest.fixture(scope="session")
async def http_client() -> AsyncGenerator[AsyncClient, None]:
    timeout = httpx.Timeout(120.0, connect=30.0)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    client = AsyncClient(timeout=timeout, headers=headers)
    yield client
