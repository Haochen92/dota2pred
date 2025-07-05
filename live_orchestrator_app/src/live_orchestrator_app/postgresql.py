import logging
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.engine.url import URL
from typing import Dict

logger = logging.getLogger(__name__)


class DatabaseEngineFactory:
    """
    Provides a singleton SQLAlchemy AsyncEngine instance per environment ('prod' or 'test')
    using baked-in configuration settings. Access via class method get_engine().
    """

    _engines: Dict[str, AsyncEngine] = {}

    # --- Baked-in Configuration ---
    _BASE_CONFIG = {
        "drivername": "postgresql+asyncpg",
        "username": "liuhaochen",
        "password": "110799",
        "host": "localhost",
        "database": "dota2",
        "pool_size": 5,
        "max_overflow": 2,
        "pool_recycle": 1800,
    }

    _ENV_PORTS = {"prod": 6000, "test": 6006}

    @classmethod
    def get_engine(cls, env: str = "prod") -> AsyncEngine:
        """
        Gets the singleton AsyncEngine instance for the specified environment.

        Args:
            env: The environment ('prod' or 'test').

        Returns:
            The singleton SQLAlchemy AsyncEngine for that environment.

        Raises:
            ValueError: If the provided env is invalid.
        """
        # Check cache first
        if env in cls._engines and cls._engines[env] is not None:
            return cls._engines[env]

        # Validate environment
        if env not in cls._ENV_PORTS:
            raise ValueError(f"Invalid environment specified: '{env}'. Use 'prod' or 'test'.")

        port = cls._ENV_PORTS[env]
        logger.info(f"Creating singleton engine instance for env '{env}' on port {port}...")

        try:
            # Create URL
            url_object = URL.create(
                drivername=cls._BASE_CONFIG["drivername"],
                username=cls._BASE_CONFIG["username"],
                password=cls._BASE_CONFIG["password"],
                host=cls._BASE_CONFIG["host"],
                port=port,
                database=cls._BASE_CONFIG["database"],
            )

            # Create engine
            engine = create_async_engine(
                url_object,
                pool_size=cls._BASE_CONFIG["pool_size"],
                max_overflow=cls._BASE_CONFIG["max_overflow"],
                pool_recycle=cls._BASE_CONFIG["pool_recycle"],
            )

            cls._engines[env] = engine
            logger.info(f"Successfully created engine for env '{env}'")
            return engine

        except Exception as e:
            logger.error(f"Failed to create engine for env '{env}': {e}", exc_info=True)
            raise

    @classmethod
    async def close_engine(cls, env: str = "prod") -> None:
        """Closes and removes the engine instance for a specific environment."""
        engine = cls._engines.pop(env, None)
        if engine:
            logger.info(f"Closing engine instance for env '{env}'...")
            await engine.dispose()
            logger.info(f"Successfully closed engine for env '{env}'")
        else:
            logger.info(f"No active engine instance found for env '{env}' to close.")

    @classmethod
    async def close_all_engines(cls) -> None:
        """Closes all managed singleton engine instances."""
        if not cls._engines:
            logger.info("No engines to close.")
            return

        logger.info("Closing all singleton database engine instances...")

        # Copy to avoid dictionary changed during iteration
        engines_to_close = list(cls._engines.items())
        cls._engines.clear()

        for env, engine in engines_to_close:
            try:
                await engine.dispose()
                logger.info(f"Closed engine for env: {env}")
            except Exception as e:
                logger.error(f"Error closing engine for env {env}: {e}")

        logger.info("Finished closing all engines.")
