import os
from contextlib import asynccontextmanager
import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.engine.url import URL

# Set up logging
logging.basicConfig(filename='lru_info.log', level=logging.ERROR)
logger = logging.getLogger(__name__)

# Singleton pattern for engine instance
_async_engine_instance = None

def get_async_engine():
    global _async_engine_instance
    if _async_engine_instance is None:
        db_url = os.environ.get("DATABASE_URL")
        if db_url:
            # Convert standard URL to async version
            if db_url.startswith('postgresql:'):
                db_url = db_url.replace('postgresql:', 'postgresql+asyncpg:', 1)
            _async_engine_instance = create_async_engine(db_url)
        else:
            # Create URL for local development
            url_object = URL.create(
                "postgresql+asyncpg",
                username='liuhaochen',
                host='localhost',
                port='6000',
                password='110799',
                database='dota2'
            )
            _async_engine_instance = create_async_engine(url_object)
    return _async_engine_instance

@asynccontextmanager
async def get_async_session():
    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            raise e