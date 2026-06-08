import asyncio
from prefect import flow
from dota_oracle_common.utils.set_logging import get_logger

logger = get_logger(__name__)
"""Register all Prefect deployments (not only daily jobs)."""


fetch_completed_matches = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/data_fetching/fetch_matches_batch.py:batch_matches_orchestrator",
)


scheduled_feature_engineering_and_inference_backfill = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/ml_pipelines/scheduled_backfill.py:scheduled_backfill_flow",
)

fetch_heros_data = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/data_fetching/fetch_hero_data.py:hero_data_orchestrator",
)

fetch_patch_data = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/data_fetching/fetch_patch_data.py:patch_data_orchestrator",
)

fetch_league_data = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/data_fetching/fetch_league_batch.py:league_data_orchestrator",
)

sync_pro_matches = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/data_fetching/sync_pro_matches.py:sync_pro_matches_flow",
)

paper_bet_replay = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/analytics/paper_bet_replay.py:paper_bet_replay_flow",
)

collect_public_matches_incremental = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/data_fetching/fetch_public_matches.py:collect_public_matches_incremental_flow",
)

backfill_public_matches_by_patches = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/data_fetching/fetch_public_matches.py:backfill_public_matches_by_patches_flow",
)

clear_prefect_cache = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/maintenance/clear_prefect_cache.py:clear_prefect_cache",
)

backup_db = flow.from_source(
    source="./",
    entrypoint="dota_oracle_schedules/maintenance/backup_db.py:backup_db_flow",
)


async def create_deployment():
    """
    Build deployments for multiple flows
    """

    await fetch_completed_matches.deploy(
        # Every 3h: at ~200-400 pro matches/day a 3h window (~25-50 matches) stays well under one
        # /proMatches page (~100), so the single un-paginated fetch covers each window with no gap.
        # (Skips matches already stored with an outcome; falls back to the paid key on a free 429.)
        name="fetch_completed_matches",
        work_pool_name="dota_oracle_scheduler",
        cron="0 */3 * * *",
        concurrency_limit=1,
    )
    logger.info("Deployment 'fetch_completed_matches' applied successfully.")

    await paper_bet_replay.deploy(
        # Once a day is plenty: paper betting has no execution, outcomes lag hours, and the replay
        # recomputes from scratch (idempotent) so a daily run settles whatever has since completed.
        # Runs at 07:00, after the 06:00 completion batch has landed fresh outcomes.
        name="paper_bet_replay",
        work_pool_name="dota_oracle_scheduler",
        cron="0 7 * * *",
        concurrency_limit=1,
    )
    logger.info("Deployment 'paper_bet_replay' applied successfully.")

    await scheduled_feature_engineering_and_inference_backfill.deploy(
        name="scheduled_feature_engineering_and_inference_backfill",
        work_pool_name="dota_oracle_scheduler",
        cron="30 0,12 * * *",  # Every day at 12:30 AM and 12:30 PM. After fetch_completed_matches
        concurrency_limit=1,
    )
    logger.info("Deployment 'scheduled_feature_engineering_and_inference_backfill' applied successfully.")

    await fetch_heros_data.deploy(
        name="fetch_heros_data", work_pool_name="dota_oracle_scheduler", cron="0 1,13 * * *", concurrency_limit=1
    )
    logger.info("Deployment 'fetch_heros_data' applied successfully.")

    await fetch_patch_data.deploy(
        name="fetch_patch_data", work_pool_name="dota_oracle_scheduler", cron="0 2,14 * * *", concurrency_limit=1
    )
    logger.info("Deployment 'fetch_patch_data' applied successfully.")

    await sync_pro_matches.deploy(name="sync_pro_matches", work_pool_name="dota_oracle_scheduler", concurrency_limit=1)

    await backfill_public_matches_by_patches.deploy(
        name="backfill_public_matches_by_patches",
        work_pool_name="dota_oracle_scheduler",
        concurrency_limit=1,
    )

    await collect_public_matches_incremental.deploy(
        name="collect_public_matches_incremental",
        work_pool_name="dota_oracle_scheduler",
        # Daily top-up from the live frontier. Frontier-bounded + free endpoint + page cap,
        # so each run is cheap regardless of how often OpenDota refreshes the sample.
        cron="0 5 * * *",
        concurrency_limit=1,
    )
    logger.info("Deployment 'collect_public_matches_incremental' applied successfully.")

    # Optional: Light weekly DB backfill (adjust window in code or trigger ad-hoc)
    # Example uses same flow; provide parameters via Prefect UI when creating runs.

    # Deploy clear prefect cache - every 3 days
    await clear_prefect_cache.deploy(
        name="clear_prefect_cache",
        work_pool_name="dota_oracle_scheduler",
        cron="0 2 */3 * *",  # Every 3 days at 2:00 AM
        concurrency_limit=1,
    )
    logger.info("Deployment 'clear_prefect_cache' applied successfully.")

    await fetch_league_data.deploy(
        name="fetch_league_data", work_pool_name="dota_oracle_scheduler", cron="0 3 * * *", concurrency_limit=1
    )
    logger.info("Deployment 'fetch_league_data' applied successfully.")

    # Manual (no schedule) DB backup deployment
    await backup_db.deploy(
        name="backup_db",
        work_pool_name="dota_oracle_scheduler",
        concurrency_limit=1,
    )
    logger.info("Deployment 'backup_db' applied successfully (manual trigger).")

    logger.info("All Prefect deployments applied successfully!")


if __name__ == "__main__":
    asyncio.run(create_deployment())
