from contextlib import asynccontextmanager
from typing import AsyncIterator

import aiohttp


@asynccontextmanager
async def aiohttp_session_provider() -> AsyncIterator[aiohttp.ClientSession]:
    """Yield one application-scoped aiohttp session and close it at shutdown."""
    async with aiohttp.ClientSession(headers={"Accept": "application/json"}) as session:
        yield session
