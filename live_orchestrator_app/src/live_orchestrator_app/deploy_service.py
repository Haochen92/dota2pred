from live_orchestrator_app.app_container import start_application
from dota_oracle_common.utils.set_logging import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    start_application.deploy(
        name="live_orchestration_app",
        work_pool_name="dota-work-pool",
        cron="*/2 * * * *",
        entrypoint="live_orchestrator_app/app_container.py:start_application",
        # every 2 minutes
    )

    logger.info(msg="Prefect Deployment successful for dota-app")
