import httpx
from contextlib import asynccontextmanager
from typing import AsyncGenerator


@asynccontextmanager
async def http_client_provider() -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    A Resource provider for a single, persistent httpx.AsyncClient that is
    shared across the entire application.
    """

    timeout = httpx.Timeout(120.0, connect=30.0)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        yield client
