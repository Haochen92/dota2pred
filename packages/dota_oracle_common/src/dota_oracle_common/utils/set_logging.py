import logging
from pythonjsonlogger.json import JsonFormatter
from logging_loki import LokiHandler
import os

# Best Practice: Default to the Docker service name, not localhost.
# In Docker, 'loki' will resolve to the loki container. 'localhost' will not.
LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100/loki/api/v1/push")

# Low-cardinality Loki labels. SERVICE_NAME distinguishes which container emitted the log
# (live-orchestrator vs api-service vs bentoml vs schedules) -- previously there was no such
# label, so logs from every service looked alike. APP_ENV separates prod from local.
SERVICE_NAME = os.getenv("SERVICE_NAME", "dota2pred")
APP_ENV = os.getenv("APP_ENV", "production")


class _CorrelationFilter(logging.Filter):
    """Attach the Prefect run ids to every record as JSON-body fields (NOT Loki labels).

    flow_run_id / task_run_id are high cardinality (one per run), so they must stay out of
    Loki's stream labels -- they go into the structured JSON line instead, letting you pivot
    Prefect <-> Loki via ``| json | flow_run_id="..."``. Resolves to empty strings outside a
    Prefect run context (api-service, bentoml, tests), so it is safe in every service.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        flow_run_id = ""
        task_run_id = ""
        try:
            from prefect.runtime import flow_run, task_run

            flow_run_id = flow_run.id or ""
            task_run_id = task_run.id or ""
        except Exception:
            pass
        record.flow_run_id = flow_run_id
        record.task_run_id = task_run_id
        return True


class LoggerSetup:
    """
    A class to handle the configuration of loggers.
    It sets up a console handler and conditionally adds a Loki handler
    based on an environment variable.
    """

    def __init__(self, loki_url: str):
        self.loki_url = loki_url
        self._correlation_filter = _CorrelationFilter()

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

        # Enrich every record with the Prefect run ids (for Loki <-> Prefect correlation).
        logger.addFilter(self._correlation_filter)

        # --- Console Handler (Always add this for local/fallback visibility) ---
        console_handler = logging.StreamHandler()
        console_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

        # --- Loki Handler (Conditional based on environment) ---
        # This is the key change. The handler is only added if you explicitly enable it.
        if os.getenv("ENABLE_LOKI_LOGGING") == "true":
            try:
                # logging-loki auto-adds `severity` (level) and `logger` (module) labels; we
                # add `service` + `env`. flow_run_id/task_run_id stay in the JSON body below.
                loki_handler = LokiHandler(
                    url=self.loki_url,
                    tags={"service": SERVICE_NAME, "env": APP_ENV},
                    version="1",
                )
                loki_handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
                logger.addHandler(loki_handler)
                # Use the root logger to print this message to avoid a potential loop
                logging.info(f"Loki handler configured for logger '{name}' (service={SERVICE_NAME}, env={APP_ENV}).")
            except Exception as e:
                logging.error(f"Failed to configure Loki handler even when enabled: {e}", exc_info=True)

        return logger


# Create a single instance that your application can import and use
_logger_setup = LoggerSetup(loki_url=LOKI_URL)
get_logger = _logger_setup.configure_logger
