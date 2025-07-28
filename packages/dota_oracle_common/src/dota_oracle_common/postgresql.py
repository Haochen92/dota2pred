from dota_oracle_common.utils.set_logging import get_logger
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from dota_oracle_common.utils.env_loader import load_workspace_env
import os

load_workspace_env()
logger = get_logger(__name__)


class DatabaseEngineFactory:
    """
    Provides a singleton SQLAlchemy AsyncEngine instance using the DATABASE_URL environment variable.
    """

    _engine: AsyncEngine | None = None

    @classmethod
    def get_engine(cls) -> AsyncEngine:
        if cls._engine is not None:
            return cls._engine

        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set. This is required.")

        try:
            # SQLAlchemy can create the engine directly from the URL string.
            # This is the standard, most reliable method.
            cls._engine = create_async_engine(database_url)

            db_name = cls._engine.url.database
            host = cls._engine.url.host
            logger.info(f"Successfully created database engine for '{db_name}' at {host}")
            return cls._engine

        except Exception as e:
            logger.error(f"Failed to create engine from DATABASE_URL: {e}", exc_info=True)
            raise

    @classmethod
    async def close_engine(cls) -> None:
        """Closes and removes the engine instance for a specific environment."""
        engine = cls._engine
        if engine:
            logger.info("Closing engine instance")
            await engine.dispose()
            cls._engine = None
            logger.info("Successfully closed engine")
        else:
            logger.info("No active engine to close")
