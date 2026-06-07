from dota_oracle_common.postgresql import DatabaseManager
from dota_oracle_common.utils import get_logger
from dota_oracle_pipeline.data_extraction.fetch_match_details import fetch_match_details
from dota_oracle_pipeline.data_extraction.api_clients.opendota_api import fetch_opendota
from dota_oracle_pipeline.data_transformation.completed_match_parser import parse_completed_matches
from dota_oracle_common.models.match import ProMatchAPIResponse, MatchTable, MatchWithOutcome, MatchOutcomeTable
from dota_oracle_common.models.utils import AsyncTask, TaskResult
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.utils.async_utils import TaskRunner
import aiohttp
from pydantic import ValidationError
from typing import List, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from prefect import flow, task
from prefect.logging import get_run_logger
from prefect.cache_policies import INPUTS
from datetime import timedelta

logger = get_logger(__name__)


@flow()
async def batch_matches_orchestrator():
    prefect_logger = get_run_logger()
    local_session = DatabaseManager.get_session_factory()
    async with local_session() as session:
        async with session.begin():
            try:
                # Fetch match_ids
                pro_match_ids = await fetch_pro_matches()
                existing_id_set = await find_existing_Ids(session, pro_match_ids)

                # Extract missing id
                missing_id_set = set(pro_match_ids) - existing_id_set

                # Fetch completed match details for missing_ids
                completed_matches = await fetch_completed_matches_concurrently(missing_id_set)

                # Store match details to db
                await store_completed_matches(session, completed_matches)
                prefect_logger.info(
                    f"""
                        Successfully completed Batch Matches fetching operations.
                        Found {len(pro_match_ids)} pro_matches, of which
                        {len(missing_id_set)} matches are missing from db.
                        Fetched and stored {len(completed_matches)}.
                    """
                )
            except Exception as e:
                prefect_logger.error(f"batch matches orchetrator failed due to error {e}", exc_info=True)
                raise


@task
async def fetch_pro_matches() -> List[int]:
    """
    Description: calls opendota's fetch_promatch endpoint without any query parameters
    Return:
    List[int]: a list of match_ids last 200 professional matches
    """
    try:
        res = await fetch_opendota(endpoint="proMatches")
        logger.info("Fetching list of pro_matches...")

        api_response = ProMatchAPIResponse.model_validate(res)
        list_instances = api_response.root
        list_match_ids = [instance.match_id for instance in list_instances]
    except (
        aiohttp.ClientConnectionError,
        aiohttp.ClientError,
        aiohttp.http.HttpProcessingError,
        ValueError,
        ValidationError,
    ) as e:
        error_message = f"{type(e).__name__}: {str(e)}"
        logger.error(error_message, exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Exception while fetching promatches, {e}", exc_info=True)
        raise

    return list_match_ids


async def find_existing_Ids(session: AsyncSession, ids_to_check: List[int]) -> Set[int]:
    """_summary_
    Extract the list of match_id in the input_list which also exists in the database

    Args:
        session (AsyncSession): database session
        ids_to_check (List[int]): a list of match ids to check

    Returns:
        Set[int]: A set of match_ids which also exists in the database
    """
    if not ids_to_check:
        return set()

    stmt = select(MatchTable.match_id).where(MatchTable.match_id.in_(ids_to_check)).where(MatchTable.outcome.has())

    results = await session.execute(stmt)

    existing_ids_in_db = set(results.scalars().all())

    return existing_ids_in_db


async def fetch_completed_matches_concurrently(match_ids_set: Set[int]) -> List[MatchWithOutcome]:

    concurrent_task_lists: List[AsyncTask[int, int, MatchWithOutcome]] = []
    for match_id in match_ids_set:
        task = AsyncTask(key=match_id, inputs=match_id, coro=fetch_and_parse_match(match_id))
        concurrent_task_lists.append(task)

    completed_matches: List[MatchWithOutcome] = []
    failure_count = 0

    res: List[TaskResult[int, int, MatchWithOutcome]] = await TaskRunner.run_concurrently(concurrent_task_lists, 20)

    for result in res:
        if isinstance(result.outcome, BaseException):
            failure_count += 1
        else:
            completed_matches.append(result.outcome)

    logger.info(
        f"""
            Successfully fetched {len(completed_matches)} matches,
            and {failure_count} matches failed
        """
    )

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
async def fetch_and_parse_match(match_id: int) -> MatchWithOutcome:
    try:
        res = await fetch_match_details(match_id)
        if not res:
            raise ValueError(f"Failed to fetch match details for match_id: {match_id}")
        parsed_match = await parse_completed_matches(res)
        return parsed_match
    except (ValueError, ValidationError) as ve:
        logger.error(f"Missing or invalid data after fetching match_id {match_id}, {ve}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while fetching match_details for match_id: {match_id}, {e}", exc_info=True)
        raise


async def store_completed_matches(session: AsyncSession, completed_matches: List[MatchWithOutcome]) -> None:

    match_details_instances: List[MatchTable] = []
    match_outcome_instances: List[MatchOutcomeTable] = []

    for match_dto in completed_matches:
        try:
            match_details_instances.append(MatchTable.model_validate(match_dto))
            match_outcome_instances.append(MatchOutcomeTable.model_validate(match_dto))
        except (ValidationError, ValueError) as ve:
            logger.warning(f"A DTO for match {match_dto.match_id} failed final validation: {ve}")
            continue

    match_repo = MatchRepository(session)

    try:
        await match_repo.insert_match_details(match_details_instances)
        await match_repo.insert_match_outcome(match_outcome_instances)

        logger.info(f"Successfully processed storage for {len(completed_matches)} matches.")

    except Exception as e:
        logger.error(f"Error encountered during the two-step storage process: {e}", exc_info=True)
        raise
