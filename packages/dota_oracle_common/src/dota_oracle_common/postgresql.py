import logging
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.engine.url import URL
from dota_oracle_common.utils.env_loader import load_workspace_env
import os

load_workspace_env()
logger = logging.getLogger(__name__)


class DatabaseEngineFactory:
    """
    Provides a singleton SQLAlchemy AsyncEngine instance per environment ('prod' or 'test')
    using baked-in configuration settings. Access via class method get_engine().
    """

    _engine: AsyncEngine | None = None

    @classmethod
    def _get_config(cls) -> dict:
        """Get current database configuration from environment variables"""
        return {
            "drivername": "postgresql+asyncpg",
            "username": os.getenv("DB_USER"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST", "localhost"),
            "database": os.getenv("DB_NAME"),
            "port": int(os.getenv("DB_PORT", "5432")),  # Convert to int
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "2")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
        }

    @classmethod
    def _validate_config(cls, config: dict) -> None:
        """Validate that all required configuration is present"""
        required_fields = ["username", "password", "database"]
        missing = [field for field in required_fields if not config.get(field)]
        if missing:
            raise ValueError(f"Missing required database configuration: {missing}")

    @classmethod
    def get_engine(cls) -> AsyncEngine:
        """
        Gets the singleton AsyncEngine instance for the specified environment.

        Returns:
            The singleton SQLAlchemy AsyncEngine for that environment.

        Raises:
            ValueError: If the provided env is invalid.
        """
        if cls._engine is not None:
            return cls._engine

        try:
            config = cls._get_config()
            cls._validate_config(config)

            # Create URL
            url_object = URL.create(
                drivername=config["drivername"],
                username=config["username"],
                password=config["password"],
                host=config["host"],
                port=config["port"],
                database=config["database"],
            )

            # Create engine
            cls._engine = create_async_engine(
                url_object,
                pool_size=config["pool_size"],
                max_overflow=config["max_overflow"],
                pool_recycle=config["pool_recycle"],
            )

            logger.info(
                f"Successfully created engine for database '{config['database']}' "
                f"at {config['host']}:{config['port']}"
            )
            return cls._engine

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
            cls._engine = None
            logger.info("Successfully closed engine")
        else:
            logger.info("No active engine to close")
