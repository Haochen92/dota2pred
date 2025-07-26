import logging
from pythonjsonlogger.json import JsonFormatter  # Correct import
import logging_loki
import os

LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100/loki/api/v1/push")


class LoggerSetup:
    """
    A class to handle the configuration of loggers.
    It sets up a console handler for local debugging and a Loki handler
    for structured, centralized logging.
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

        if logger.hasHandlers():
            return logger

        # --- Console Handler (for simple local output) ---
        console_handler = logging.StreamHandler()
        console_format = logging.Formatter("%(name)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

        # --- Loki Handler (for sending logs to Grafana) ---
        try:
            loki_handler = logging_loki.LokiHandler(
                url=self.loki_url,
                tags={"application": name},  # This tag will be searchable in Grafana
                version="1",
            )
            # This formatter ensures the log message and any 'extra' data is sent as JSON
            loki_handler.setFormatter(JsonFormatter())  # Using the corrected import
            logger.addHandler(loki_handler)
        except Exception as e:
            # Fallback if Loki is not available
            logger.warning(f"Failed to configure Loki handler: {e}")

        return logger


# Create a single instance that your application can import and use
_logger_setup = LoggerSetup(loki_url=LOKI_URL)
get_logger = _logger_setup.configure_logger
