import asyncio
from datetime import timedelta
from typing import List, Optional, Set, Tuple

from pydantic import ValidationError

# Use the standard MatchRepository, which now has the upsert method
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.models.match import MatchWithOutcome, ProMatchOutcome, ProMatchAPIResponse

from dota_oracle_common.models.utils import AsyncTask, TaskResult
from dota_oracle_common.postgresql import DatabaseManager
from dota_oracle_common.utils import get_logger
from dota_oracle_common.utils.async_utils import TaskRunner
from dota_oracle_pipeline.data_extraction.api_clients.opendota_api import fetch_opendota_api
from dota_oracle_pipeline.data_extraction.fetch_match_details import fetch_match_details
from .fetch_matches_batch import find_existing_Ids
from dota_oracle_pipeline.data_transformation.completed_match_parser import parse_completed_matches
from prefect import flow, task
from prefect.cache_policies import INPUTS
from prefect.logging import get_run_logger

logger = get_logger(__name__)


# ==============================================================================
# The Flow with the Main Pagination Loop
# ==============================================================================
@flow(name="Sync Pro Matches")
async def sync_pro_matches_flow(
    start_after_match_id: int, less_than_match_id: Optional[int] = None, concurrent_requests_limit: int = 20
):
    """
    Finds and processes pro matches page-by-page directly within the flow.

    In each step of its main loop, this flow:
    1. Fetches one page of recent pro matches from the OpenDota API.
    2. Filters them to find matches newer than our 'start_after_match_id' bookmark.
    3. Triggers a sub-task to fetch full details for that batch and upsert them.
    4. Continues to the next page until the bookmark is reached.
    """
    prefect_logger = get_run_logger()
    local_session = DatabaseManager.get_session_factory()
    total_processed_count = 0
    stop_pagination = False

    current_less_than_match_id = less_than_match_id

    if current_less_than_match_id:
        prefect_logger.info(f"Starting targeted sync from matches older than {current_less_than_match_id}.")
    else:
        prefect_logger.info("Starting sync from the latest pro matches.")
    prefect_logger.info(f"Sync will stop when it reaches matches older than or equal to {start_after_match_id}.")

    while not stop_pagination:
        try:
            prefect_logger.info(
                f"Fetching next page of pro matches before ID: {current_less_than_match_id or 'Most Recent'}"
            )

            validated_matches, next_cursor = await fetch_and_validate_pro_matches_page(current_less_than_match_id)

            if not validated_matches and not next_cursor:
                prefect_logger.info("Received an empty or invalid page from API. Sync complete.")
                break

            current_less_than_match_id = next_cursor

            match_ids_to_process = []
            for match in sorted(validated_matches, key=lambda m: m.match_id, reverse=True):
                if match.match_id > start_after_match_id:
                    match_ids_to_process.append(match.match_id)
                else:
                    prefect_logger.info(
                        f"Reached match {match.match_id}, which is not newer than {start_after_match_id}. This will be the last page."
                    )
                    stop_pagination = True
                    break

            if match_ids_to_process:
                processed_count = await process_match_batch(
                    match_ids=match_ids_to_process,
                    concurrency_limit=concurrent_requests_limit,
                    session_factory=local_session,
                )
                total_processed_count += processed_count
            elif not stop_pagination:  # Only log this if we're not about to stop anyway
                prefect_logger.info("No new matches to process on this page, but continuing to next.")

            if not current_less_than_match_id:
                prefect_logger.info("No further pages to fetch. Sync complete.")
                break

            await asyncio.sleep(1)

        except Exception as e:
            prefect_logger.error(f"A critical error occurred in the main sync loop: {e}", exc_info=True)
            raise

    prefect_logger.info(
        f"Sync Pro Matches flow completed successfully. "
        f"Total matches processed and upserted: {total_processed_count}."
    )


# ==============================================================================
# Helper Functions and Sub-Tasks
# ==============================================================================
async def fetch_and_validate_pro_matches_page(
    less_than_match_id: Optional[int],
) -> Tuple[List[ProMatchOutcome], Optional[int]]:
    """
    Fetches one page, validates it, and returns the clean data and next cursor.
    """
    prefect_logger = get_run_logger()

    params = {}
    if less_than_match_id:
        params["less_than_match_id"] = less_than_match_id
    raw_page_data = await fetch_opendota_api(endpoint="/proMatches", params=params)

    if not raw_page_data or not isinstance(raw_page_data, list):
        return [], None

    next_cursor = None
    try:
        all_ids_on_page = [m["match_id"] for m in raw_page_data if "match_id" in m]
        if all_ids_on_page:
            next_cursor = min(all_ids_on_page)
    except (TypeError, KeyError):
        prefect_logger.warning("Could not extract match_ids from raw page data.")

    try:
        validated_response = ProMatchAPIResponse.model_validate(raw_page_data)
        matches_with_outcome = [m for m in validated_response.root if m.radiant_win is not None]
        return matches_with_outcome, next_cursor
    except ValidationError as ve:
        prefect_logger.warning(f"Data on page failed validation and will be skipped. Error: {ve}")
        return [], next_cursor


@task(name="Process Match Batch")
async def process_match_batch(match_ids: List[int], concurrency_limit: int, session_factory) -> int:
    """Fetches details for a batch of matches and upserts them into the DB."""
    prefect_logger = get_run_logger()

    # Skip matches we already have complete (present in the DB *with* an outcome) so a deep
    # backfill only pays for genuinely-missing matches. find_existing_Ids filters on
    # MatchTable + an outcome row, so present-but-outcomeless matches are still re-fetched.
    async with session_factory() as session:
        existing_ids = await find_existing_Ids(session, match_ids)
    missing_ids = [mid for mid in match_ids if mid not in existing_ids]

    if not missing_ids:
        prefect_logger.info(f"All {len(match_ids)} matches in this batch already stored; skipping.")
        return 0

    prefect_logger.info(
        f"Processing {len(missing_ids)}/{len(match_ids)} missing matches "
        f"(from {missing_ids[0]} to {missing_ids[-1]})"
    )

    completed_matches = await fetch_completed_matches_concurrently(set(missing_ids), concurrency_limit)

    if not completed_matches:
        prefect_logger.warning("No matches in this batch were successfully fetched/parsed.")
        return 0

    async with session_factory() as session:
        async with session.begin():
            repo = MatchRepository(session)
            await repo.upsert_match_with_outcome(completed_matches)

    prefect_logger.info(f"Successfully committed {len(completed_matches)} upserts for this batch.")
    return len(completed_matches)


async def fetch_completed_matches_concurrently(
    match_ids_set: Set[int], concurrency_limit: int = 20
) -> List[MatchWithOutcome]:
    """Concurrently fetches and parses match details for a given set of match IDs."""
    if not match_ids_set:
        return []

    task_list = [AsyncTask(key=mid, inputs=mid, coro=fetch_and_parse_match(mid)) for mid in match_ids_set]
    results: List[TaskResult] = await TaskRunner.run_concurrently(task_list, concurrency_limit)

    completed_matches = [res.outcome for res in results if not isinstance(res.outcome, BaseException)]
    failed_count = len(results) - len(completed_matches)

    if failed_count > 0:
        logger.warning(f"{failed_count} matches failed to fetch/parse.")

    return completed_matches


@task(
    name="fetch_and_parse_match",
    retries=3,
    retry_delay_seconds=10,
    cache_policy=INPUTS,
    cache_expiration=timedelta(days=1),
    # Explicit persist so the API-cost cache keeps working even with
    # PREFECT_RESULTS_PERSIST_BY_DEFAULT disabled globally.
    persist_result=True,
)
async def fetch_and_parse_match(match_id: int) -> Optional[MatchWithOutcome]:
    """Fetches details for a single match and parses it."""
    try:
        res = await fetch_match_details(match_id)
        if not res:
            raise ValueError(f"No data returned for match_id: {match_id}")
        return await parse_completed_matches(res)
    except (ValueError, ValidationError) as ve:
        logger.error(f"Data validation error for match_id {match_id}: {ve}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching match {match_id}: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # --- Example of a BACKFILL run ---
    # Imagine you want to re-process all matches between 7,300,000,000 and 7,290,000,000
    BACKFILL_START_POINT = None
    BACKFILL_STOP_POINT = 7290000000

    # For a simple local run, use asyncio.run
    asyncio.run(
        sync_pro_matches_flow(
            start_after_match_id=BACKFILL_STOP_POINT,
            less_than_match_id=BACKFILL_START_POINT,
            concurrent_requests_limit=15,
        )
    )
