from typing import List, Optional
import os

from prefect import flow
from sqlalchemy import select

from dota_oracle_common.utils import get_logger, load_workspace_env
from dota_oracle_common.postgresql import DatabaseManager
from dota_oracle_common.models.patches import PatchTable
from dota_oracle_common.repositories.public_match_repository import PublicMatchRepository
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

# Incremental top-up collector knobs. Defaults are deliberately cheap: page from the live
# frontier down, on the FREE endpoint, throttled, with a hard per-run page cap.
INCREMENTAL_MAX_PAGES = int(os.getenv("PUBLIC_MATCH_INCREMENTAL_MAX_PAGES", "200"))
INCREMENTAL_PER_PAGE_SLEEP = float(os.getenv("PUBLIC_MATCH_INCREMENTAL_SLEEP", "1.5"))
INCREMENTAL_USE_PAID = os.getenv("PUBLIC_MATCH_INCREMENTAL_USE_PAID", "false").lower() == "true"

# Cap the rolling public_matches window. Oldest rows (lowest match_id) are trimmed after
# each top-up so the table stays bounded instead of growing forever.
MAX_PUBLIC_MATCH_ROWS = int(os.getenv("PUBLIC_MATCH_MAX_ROWS", "500000"))
TRIM_BATCH_SIZE = int(os.getenv("PUBLIC_MATCH_TRIM_BATCH", "20000"))


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


@flow(name="Collect Public Matches Incremental")
async def collect_public_matches_incremental_flow(
    min_rank: int = DEFAULT_MIN_RANK,
    max_rank: int = DEFAULT_MAX_RANK,
    max_pages: int = INCREMENTAL_MAX_PAGES,
    per_page_sleep: float = INCREMENTAL_PER_PAGE_SLEEP,
    use_paid: bool = INCREMENTAL_USE_PAID,
    max_rows: int = MAX_PUBLIC_MATCH_ROWS,
) -> None:
    """
    Top up `public_matches` from the live frontier.

    Pages OpenDota's /publicMatches from the newest matches down to the highest match_id we
    already store, inserting only net-new rows. /publicMatches serves a periodically-refreshed
    *sample* of unknown cadence, so runs are driven by the frontier stop -- a run is cheap
    whether or not the sample changed since last time. Replaces the old
    per-patch-after-14-days collector, which paged through hundreds of millions of
    already-unfetchable historical ids for zero inserts (and the bulk of the API bill).
    """
    session_factory = DatabaseManager.get_session_factory()
    async with session_factory() as session:
        repo = PublicMatchRepository(session)
        frontier = await repo.get_max_match_id()

    if frontier is None:
        logger.warning("public_matches is empty; first run will collect whatever the current sample serves.")
        frontier = 0

    collector = _build_collector(DatabaseManager.get_session_factory(), min_rank=min_rank, max_rank=max_rank)
    result = await collector.collect_incremental(
        start_match_id=MAX_MATCH_ID_CURSOR,
        frontier_match_id=frontier,
        max_pages=max_pages,
        per_page_sleep=per_page_sleep,
        use_paid=use_paid,
    )
    logger.info(
        f"Incremental public-match collection inserted {result['total_new']} new rows (frontier was {frontier})."
    )

    # Keep the rolling window bounded: drop the oldest rows beyond the cap.
    async with DatabaseManager.get_session_factory()() as session:
        repo = PublicMatchRepository(session)
        trimmed = await repo.trim_to_max_rows(max_rows=max_rows, batch_size=TRIM_BATCH_SIZE)
    logger.info(f"Trimmed {trimmed} old public_matches rows (cap {max_rows}).")


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
