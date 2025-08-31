import asyncio
from prefect import flow
from dota_oracle_common.utils.set_logging import get_logger

logger = get_logger(__name__)
# Hot reload test comment


fetch_completed_matches = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/data_fetching/fetch_matches_batch.py:batch_matches_orchestrator",
)

fetch_heros_data = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/data_fetching/fetch_hero_data.py:hero_data_orchestrator",
)

clear_prefect_cache = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/maintenance/clear_prefect_cache.py:clear_prefect_cache",
)


async def create_deployment():
    """
    Build deployments for multiple flows
    """

    await fetch_completed_matches.deploy(
        name="fetch_completed_matches", work_pool_name="dota_oracle_scheduler", cron="0 0,12 * * *", concurrency_limit=1
    )
    logger.info("Deployment 'fetch_completed_matches' applied successfully.")

    await fetch_heros_data.deploy(
        name="fetch_heros_data", work_pool_name="dota_oracle_scheduler", cron="0 1,13 * * *", concurrency_limit=1
    )
    logger.info("Deployment 'fetch_heros_data' applied successfully.")

    # Deploy clear prefect cache - every 3 days
    await clear_prefect_cache.deploy(
        name="clear_prefect_cache",
        work_pool_name="dota_oracle_scheduler",
        cron="0 2 */3 * *",  # Every 3 days at 2:00 AM
        concurrency_limit=1,
    )
    logger.info("Deployment 'clear_prefect_cache' applied successfully.")

    logger.info("All Prefect deployments applied successfully!")


if __name__ == "__main__":
    asyncio.run(create_deployment())
