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
        "username": "liuhaochen",      # Replace with your actual user
        "password": "110799",          # Replace or load from env var for safety
        "host": "localhost",
        "database": "dota2",           # Replace with your actual DB name
        "echo_sql": False,
        # Basic pooling defaults (SQLAlchemy uses QueuePool by default)
        "pool_size": 5,               # Minimal pool size
        "max_overflow": 2             # Minimal overflow
    }
    _ENV_PORTS = {
        "prod": 6000,
        "test": 6030                  # Changed test port as requested
    }

    @classmethod
    def get_engine(cls, env: str = 'prod') -> AsyncEngine:
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

        # --- Engine Creation Logic ---
        if env not in cls._ENV_PORTS:
            raise ValueError(f"Invalid environment specified: '{env}'. Use 'prod' or 'test'.")

        port = cls._ENV_PORTS[env]
        logger.info(f"Creating singleton engine instance for env '{env}' on port {port}...")

        config = cls._BASE_CONFIG.copy() # Start with base config
        config['port'] = port           # Add the environment-specific port

        try:
            url_object = URL.create(**config) # Create URL from combined config

            engine = create_async_engine(
                url_object,
                pool_size=config['pool_size'],
                max_overflow=config['max_overflow'],
                pool_recycle=1800, 
                echo=config['echo_sql']
            )
            cls._engines[env] = engine 
            return engine

        except Exception as e:
            logger.error(f"Failed to create engine for env '{env}': {e}", exc_info=True)
            raise 

    @classmethod
    async def close_engine(cls, env: str = 'prod'):
        """Closes and removes the engine instance for a specific environment."""
        engine = cls._engines.pop(env, None)
        if engine:
            logger.info(f"Closing engine instance for env '{env}'...")
            await engine.dispose()
        else:
             logger.info(f"No active engine instance found for env '{env}' to close.")

    @classmethod
    async def close_all_engines(cls):
        """Closes all managed singleton engine instances."""
        logger.info("Closing all singleton database engine instances...")
        items = list(cls._engines.items())
        cls._engines.clear()

        for env, engine in items:
             try:
                 await engine.dispose()
                 logger.info(f"Closed engine for env: {env}")
             except Exception as e:
                 logger.error(f"Error closing engine for env {env}: {e}")
        logger.info("Finished closing all engines.")
