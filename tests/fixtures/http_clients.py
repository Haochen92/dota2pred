import pytest
from unittest.mock import AsyncMock
import httpx
import aiohttp
import respx
from typing import AsyncGenerator, Iterator
from httpx import AsyncClient
from dota_oracle_pipeline.data_extraction.api_clients.opendota_api import OpenDotaClient
from dota_oracle_pipeline.data_extraction.api_clients.steam_api import SteamClient


# =================================================================================
# LEVEL 1: UNIT TESTS (Dependency Injection)
# =================================================================================


@pytest.fixture
def mock_http_client() -> AsyncMock:
    """Provides a mock `httpx.AsyncClient` for white-box unit testing.

    Use for dependency injection into services or classes that receive a client
    as a parameter, allowing for testing in complete isolation.
    """
    return AsyncMock(spec=httpx.AsyncClient)


@pytest.fixture
def mock_aiohttp_session() -> AsyncMock:
    return AsyncMock(spec=aiohttp.ClientSession)


@pytest.fixture
def mock_opendota_client() -> AsyncMock:
    return AsyncMock(spec=OpenDotaClient)


@pytest.fixture
def mock_steam_client() -> AsyncMock:
    return AsyncMock(spec=SteamClient)


# =================================================================================
# LEVEL 2: API LAYER TESTS (Network Interception)
# =================================================================================


@pytest.fixture
def respx_mock() -> Iterator[respx.MockRouter]:
    """Provides an active `respx` router to intercept outgoing HTTP calls.

    This is the foundational fixture for isolated API layer tests. It enables
    network mocking for fixtures like `api_layer_client`.
    """
    with respx.mock as mock:
        yield mock


# =================================================================================
# Fixtures for actual HTTP client connections
# =================================================================================


@pytest.fixture(scope="session")
async def http_client() -> AsyncGenerator[AsyncClient, None]:
    timeout = httpx.Timeout(120.0, connect=30.0)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    client = AsyncClient(timeout=timeout, headers=headers)
    yield client
