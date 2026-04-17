import logging
from pythonjsonlogger.json import JsonFormatter
from logging_loki import LokiHandler
import os

# Best Practice: Default to the Docker service name, not localhost.
# In Docker, 'loki' will resolve to the loki container. 'localhost' will not.
LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100/loki/api/v1/push")


class LoggerSetup:
    """
    A class to handle the configuration of loggers.
    It sets up a console handler and conditionally adds a Loki handler
    based on an environment variable.
    """

    def __init__(self, loki_url: str):
        self.loki_url = loki_url

    def configure_logger(self, name: str) -> logging.Logger:
        """
        Configures and returns a logger instance.
        Avoids adding duplicate handlers if called multiple times.
        """
        logger = logging.getLogger(name)
        logger.propagate = False
        logger.setLevel(logging.INFO)

        # If handlers are already configured, don't add more.
        if logger.hasHandlers():
            return logger

        # --- Console Handler (Always add this for local/fallback visibility) ---
        console_handler = logging.StreamHandler()
        console_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

        # --- Loki Handler (Conditional based on environment) ---
        # This is the key change. The handler is only added if you explicitly enable it.
        if os.getenv("ENABLE_LOKI_LOGGING") == "true":
            try:
                loki_handler = LokiHandler(
                    url=self.loki_url,
                    tags={"application": name},
                    version="1",
                )
                loki_handler.setFormatter(JsonFormatter())
                logger.addHandler(loki_handler)
                # Use the root logger to print this message to avoid a potential loop
                logging.info(f"Loki handler configured for logger '{name}'.")
            except Exception as e:
                logging.error(f"Failed to configure Loki handler even when enabled: {e}", exc_info=True)

        return logger


# Create a single instance that your application can import and use
_logger_setup = LoggerSetup(loki_url=LOKI_URL)
get_logger = _logger_setup.configure_logger
