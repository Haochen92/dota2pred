import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from dota_oracle_common.utils.env_loader import load_workspace_env
from dota_oracle_common.utils.set_logging import get_logger


load_workspace_env()
logger = get_logger(__name__)


class DatabaseManager:
    """Own one SQLAlchemy engine and its session factory."""

    def __init__(
        self,
        database_url: str | None = None,
        pool_size: int | None = None,
        max_overflow: int | None = None,
    ) -> None:
        resolved_url = database_url or os.getenv("DATABASE_URL")
        if not resolved_url:
            raise ValueError("DATABASE_URL environment variable not set. This is required.")

        resolved_pool_size = pool_size if pool_size is not None else int(os.getenv("DB_POOL_SIZE", "5"))
        resolved_max_overflow = max_overflow if max_overflow is not None else int(os.getenv("DB_MAX_OVERFLOW", "10"))

        logger.info(
            f"Creating database engine with pool_size={resolved_pool_size} and max_overflow={resolved_max_overflow}"
        )
        self._engine: AsyncEngine = create_async_engine(
            resolved_url,
            pool_size=resolved_pool_size,
            max_overflow=resolved_max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info(f"Successfully initialized database for '{self._engine.url.database}' at {self._engine.url.host}")

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    async def close_engine(self) -> None:
        """Dispose this manager's connection pool."""
        logger.info("Closing database engine")
        await self._engine.dispose()
        logger.info("Successfully closed database engine")


@asynccontextmanager
async def database_session_factory_resource(
    database_url: str | None = None,
    pool_size: int | None = None,
    max_overflow: int | None = None,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Yield an application-scoped session factory and dispose its engine at shutdown."""
    database = DatabaseManager(
        database_url=database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )
    try:
        yield database.session_factory
    finally:
        await database.close_engine()
