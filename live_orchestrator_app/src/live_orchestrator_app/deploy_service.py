import asyncio
from prefect import flow
from dota_oracle_common.utils.set_logging import get_logger

logger = get_logger(__name__)


async def create_deployment():
    """
    Builds a Prefect Deployment object with a specific entrypoint
    and applies it to the Prefect server.
    """

    flow_from_file = await flow.from_source(
        source="./",
        entrypoint="live_orchestrator_app/app_container.py:start_application",
    )  # type: ignore

    await flow_from_file.deploy(
        name="live_orchestration_app", work_pool_name="dota-work-pool", cron="*/2 * * * *", concurrency_limit=1
    )  # type: ignore
    logger.info("Prefect Deployment 'live_orchestration_app' applied successfully.")


if __name__ == "__main__":
    asyncio.run(create_deployment())
