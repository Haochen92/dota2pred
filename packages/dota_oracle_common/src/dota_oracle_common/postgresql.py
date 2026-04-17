import os
from typing import Optional

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.env_loader import load_workspace_env

load_workspace_env()
logger = get_logger(__name__)


class DatabaseManager:
    """
    Manages a singleton SQLAlchemy engine and provides a session factory.
    This class is designed to be initialized once at application startup.
    """

    _engine: Optional[AsyncEngine] = None
    _session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    @classmethod
    def _initialize(cls) -> None:
        """
        Internal method to create the engine and session factory.
        This is called automatically by the public methods if needed.
        """
        if cls._engine is not None:
            return

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set. This is required.")

        try:
            pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
            max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))

            logger.info(f"Creating database engine with pool_size={pool_size} and max_overflow={max_overflow}")

            cls._engine = create_async_engine(
                database_url,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
            )

            # Create the session factory and bind it to the engine.
            cls._session_factory = async_sessionmaker(
                bind=cls._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            db_name = cls._engine.url.database
            host = cls._engine.url.host
            logger.info(f"Successfully initialized database for '{db_name}' at {host}")

        except Exception as e:
            logger.error(f"Failed to initialize database from DATABASE_URL: {e}", exc_info=True)
            raise

    @classmethod
    def get_session_factory(cls) -> async_sessionmaker[AsyncSession]:
        """
        Returns the singleton session factory.
        Initializes the database engine on the first call.
        """
        cls._initialize()
        if not cls._session_factory:
            raise RuntimeError("Session factory could not be created.")
        return cls._session_factory

    @classmethod
    async def get_session(cls) -> AsyncSession:
        """
        A convenience method to get a single session instance directly.
        Useful for simple, one-off operations.
        """
        factory = cls.get_session_factory()
        return factory()

    @classmethod
    async def close_engine(cls) -> None:
        """Closes the underlying engine's connection pool."""
        if cls._engine:
            logger.info("Closing database engine instance")
            await cls._engine.dispose()
            cls._engine = None
            cls._session_factory = None  # Clear the factory as well
            logger.info("Successfully closed database engine")
        else:
            logger.info("No active engine to close")
