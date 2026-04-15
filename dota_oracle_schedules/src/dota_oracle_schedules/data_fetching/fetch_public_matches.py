from typing import List, Optional
import os
from datetime import datetime, timezone, timedelta

from prefect import flow
from sqlalchemy import select

from dota_oracle_common.utils import get_logger, load_workspace_env
from dota_oracle_common.postgresql import DatabaseManager
from dota_oracle_common.models.patches import PatchTable
from dota_oracle_pipeline.data_extraction.public_match_collector import PublicMatchCollector


load_workspace_env()
logger = get_logger(__name__)


# Default params (env-overridable)
DEFAULT_MIN_RANK = int(os.getenv("PUBLIC_MATCH_MIN_RANK", "80"))
DEFAULT_MAX_RANK = int(os.getenv("PUBLIC_MATCH_MAX_RANK", "85"))
MAX_MATCH_ID_CURSOR = int(os.getenv("PUBLIC_MATCH_MAX_MATCH_ID", "9999999999999"))
ERROR_HOP_MATCH_IDS = int(os.getenv("PUBLIC_MATCH_ERROR_HOP", "5000"))
HOP_MAX = int(os.getenv("PUBLIC_MATCH_HOP_MAX", "40000"))
INSERT_BATCH_SIZE = int(os.getenv("PUBLIC_MATCH_DB_BATCH", "1000"))
MAX_PASSES = int(os.getenv("PUBLIC_MATCH_MAX_PASSES", "3"))
HOP_ON_NO_PROGRESS = int(os.getenv("PUBLIC_MATCH_HOP_ON_NO_PROGRESS", "0"))
PASS_BACKOFF_SECONDS = int(os.getenv("PUBLIC_MATCH_PASS_BACKOFF", "0"))


def _build_collector(session_factory, *, min_rank: int, max_rank: int):
    return PublicMatchCollector(
        session_factory=session_factory,
        min_rank=min_rank,
        max_rank=max_rank,
        insert_batch_size=INSERT_BATCH_SIZE,
        error_hop_match_ids=ERROR_HOP_MATCH_IDS,
        hop_max=HOP_MAX,
        max_passes=MAX_PASSES,
        hop_on_no_progress=HOP_ON_NO_PROGRESS,
        backoff_seconds_between_passes=PASS_BACKOFF_SECONDS,
    )


@flow(name="Collect Public Matches For Latest Patch")
async def collect_public_matches_for_latest_patch_flow(
    matches_to_collect: int = 50000,
    min_rank: int = DEFAULT_MIN_RANK,
    max_rank: int = DEFAULT_MAX_RANK,
) -> None:
    """
    Entry flow to collect public matches for the latest patch after a 2-week delay.

    - Finds the latest patch (where end_time is NULL).
    - Skips run if patch age < 14 days.
    - Requires hydrated `start_match_id` on the patch row.
    """
    session_factory = DatabaseManager.get_session_factory()
    async with session_factory() as session:
        stmt = select(PatchTable).where(PatchTable.end_time.is_(None)).order_by(PatchTable.start_time.desc()).limit(1)
        result = await session.execute(stmt)
        latest_patch: Optional[PatchTable] = result.scalar_one_or_none()

        if latest_patch is None:
            logger.critical("No latest patch found (end_time IS NULL). Aborting collection.")
            return

        # Enforce 2-week delay from patch start_time
        now = datetime.now(timezone.utc)
        threshold = (latest_patch.start_time or now) + timedelta(days=14)
        if now < threshold:
            logger.info(
                f"Latest patch {latest_patch.patch_number} is younger than 14 days. Skipping until {threshold.isoformat()}"
            )
            return

        if latest_patch.start_match_id is None:
            logger.critical("Latest patch is missing start_match_id. Run hydrate_patch_boundaries_task() first.")
            return

        # For the latest patch (open-ended), start from the most recent matches and stop at start_match_id
        start_id = MAX_MATCH_ID_CURSOR
        end_id = latest_patch.start_match_id

    collector = _build_collector(DatabaseManager.get_session_factory(), min_rank=min_rank, max_rank=max_rank)
    await collector.collect_range(
        start_match_id=start_id,
        end_match_id=end_id,
        target_match_count=matches_to_collect,
    )


@flow(name="Backfill Public Matches By Patches")
async def backfill_public_matches_by_patches_flow(
    patch_numbers: List[str],
    matches_per_patch: int = 30000,
    min_rank: int = DEFAULT_MIN_RANK,
    max_rank: int = DEFAULT_MAX_RANK,
) -> None:
    """
    Manually trigger backfill for specific patch versions.
    Skips any patch not found or missing boundaries.
    """
    session_factory = DatabaseManager.get_session_factory()
    async with session_factory() as session:
        for pnum in patch_numbers:
            stmt = select(PatchTable).where(PatchTable.patch_number == pnum)
            res = await session.execute(stmt)
            patch: Optional[PatchTable] = res.scalar_one_or_none()
            if patch is None:
                logger.warning(f"Patch {pnum} not found. Skipping.")
                continue
            if patch.start_match_id is None or patch.end_match_id is None:
                logger.warning(f"Patch {pnum} is missing boundaries. Skipping.")
                continue

            start_id = patch.end_match_id
            end_id = patch.start_match_id

            logger.info(
                f"Backfilling patch {pnum} between match_id [{end_id}, {start_id}] up to {matches_per_patch} unique matches."
            )
            collector = _build_collector(DatabaseManager.get_session_factory(), min_rank=min_rank, max_rank=max_rank)
            await collector.collect_range(
                start_match_id=start_id,
                end_match_id=end_id,
                target_match_count=matches_per_patch,
            )
