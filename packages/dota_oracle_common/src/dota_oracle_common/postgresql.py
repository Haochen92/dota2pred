import logging
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.engine.url import URL
from dota_oracle_common.utils.env_loader import load_workspace_env
import os

logger = logging.getLogger(__name__)

class DatabaseEngineFactory:
    """
    Provides a singleton SQLAlchemy AsyncEngine instance per environment ('prod' or 'test')
    using baked-in configuration settings. Access via class method get_engine().
    """
    _engine: AsyncEngine

    # --- Baked-in Configuration ---
    _BASE_CONFIG = {
        "drivername": "postgresql+asyncpg",
        "username": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": "localhost",
        "database": os.getenv("DB_NAME"),
        "port": os.getenv("DB_PORT"),
        "pool_size": 5,
        "max_overflow": 2,
        "pool_recycle": 1800,
    }
    

    @classmethod
    def get_engine(cls) -> AsyncEngine:
        """
        Gets the singleton AsyncEngine instance for the specified environment.

        Returns:
            The singleton SQLAlchemy AsyncEngine for that environment.

        Raises:
            ValueError: If the provided env is invalid.
        """

        try:
            # Create URL
            url_object = URL.create(
                drivername=cls._BASE_CONFIG["drivername"],
                username=cls._BASE_CONFIG["username"],
                password=cls._BASE_CONFIG["password"],
                host=cls._BASE_CONFIG["host"],
                port=cls._BASE_CONFIG["port"],
                database=cls._BASE_CONFIG["database"]
            )

            # Create engine
            engine = create_async_engine(
                url_object,
                pool_size=cls._BASE_CONFIG["pool_size"],
                max_overflow=cls._BASE_CONFIG["max_overflow"],
                pool_recycle=cls._BASE_CONFIG["pool_recycle"],
            )
            
            cls._engines = engine
            logger.info(
                "Successfully created engine, "
                f"database name: {cls._BASE_CONFIG['database']}, "
                f"at {cls._BASE_CONFIG['host']}:{cls._BASE_CONFIG['port']}"
            )
            return engine

        except Exception as e:
            logger.error(f"Failed to create engine: {e}", exc_info=True)
            raise 

    @classmethod
    async def close_engine(cls) -> None:
        """Closes and removes the engine instance for a specific environment."""
        engine = cls._engine
        if engine:
            logger.info("Closing engine instance")
            await engine.dispose()
            logger.info("Successfully closed engine")
        else:
            logger.info("No active engine to close")
