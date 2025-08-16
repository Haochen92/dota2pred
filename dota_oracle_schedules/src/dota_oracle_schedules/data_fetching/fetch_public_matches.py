from prefect import flow, task
from typing import List
from dota_oracle_common.models.match import PublicMatch, PublicMatchAPIResponse
from dota_oracle_pipeline.data_extraction.api_clients import fetch_opendota_api
from dota_oracle_common.utils import get_logger, load_workspace_env
from dota_oracle_common.s3 import S3Wrapper
import pandas as pd
import datetime as dt
import asyncio
import os
from pathlib import Path

load_workspace_env()

logger = get_logger(__name__)

loki_url = os.getenv("LOKI_URL")
enable_loki_logging = os.getenv("ENABLE_LOKI_LOGGING")
print("loki_url: ", loki_url)
print("enable logging?: ", enable_loki_logging)


# FILEPATH
SCRIPT_PATH = Path(__file__).resolve()
DATA_DIR = SCRIPT_PATH.parent.parent / "data"
F_PATH = DATA_DIR / "publicMatches.parquet"

# S3 Object Prefix
S3_OBJECT_PREFIX = "dota2pred/archives/public_matches/"

# Params Constants
MAX_MATCH_ID = 999999999999999
MATCH_COUNT_LIMIT = 100000
MIN_RANK = 30  # Crusader
MAX_RANK = 65  # Legend
END_POINT = "publicMatches"
BATCH_HOP_ON_FAILURE = 100


@flow()
async def public_match_orchestrator():
    """Orchestrates fetching matches, archiving old data, and saving new data."""
    try:
        await archive_local_file_to_s3()
        all_matches = await fetch_all_matches()
        await save_matches_locally(all_matches)
        logger.info("public_match_orchestration_cycle complete")
    except Exception as e:
        logger.error(f"Process failed with Error {str(e)}", exc_info=True)
        raise


@task
async def fetch_all_matches():
    """Fethes a target number of unique matches using the /publicMatches endpoint."""
    current_max_match_id = MAX_MATCH_ID
    all_public_matches = []
    collected_match_ids = set()

    while len(collected_match_ids) < MATCH_COUNT_LIMIT:
        try:
            logger.info(
                f"Collected {len(collected_match_ids)}/{MATCH_COUNT_LIMIT}. Fetching batch < {current_max_match_id}..."
            )

            matches_batch = await fetch_one_batch(current_max_match_id)

            if not matches_batch:
                logger.warning("Received an empty batch, assuming end of data. Stopping.")
                break

            for match in matches_batch:
                if match.match_id not in collected_match_ids:
                    collected_match_ids.add(match.match_id)
                    all_public_matches.append(match)

            logger.info(f"Collected {len(collected_match_ids)} unique matches")

            current_max_match_id = get_min_match_id(matches_batch)

        except Exception as e:
            logger.error(f"An error occurred in the main loop: {e}", exc_info=True)
            logger.warning(f"Skipping range by hopping down by {BATCH_HOP_ON_FAILURE}.")
            current_max_match_id -= BATCH_HOP_ON_FAILURE
            continue

    logger.info(f"Successfully fetched {len(all_public_matches)} unique matches.")
    return all_public_matches[:MATCH_COUNT_LIMIT]


async def fetch_one_batch(less_than_match_id: int) -> List[PublicMatch]:
    """
    Fetch 1 batch of matches from Opendota publicMatch endpoint
    """

    res = await fetch_opendota_api(
        endpoint=END_POINT,
        params={"less_than_match_id": less_than_match_id, "min_rank": MIN_RANK, "max_rank": MAX_RANK},
    )

    validated_response = PublicMatchAPIResponse.model_validate(res)
    list_public_matches = validated_response.root

    return list_public_matches


def get_min_match_id(match_list: List[PublicMatch]) -> int:
    if not match_list:
        return 0
    match_id_list = [match.match_id for match in match_list]

    return min(match_id_list)


@task
async def save_matches_locally(matches: List[PublicMatch]):
    """
    upload previous parquet file to s3
    delete old file from fpath
    serialise current matches into pq
    store latest pq into fpath
    """
    try:
        data_list = [match.model_dump() for match in matches]
        df = pd.DataFrame(data_list)
        logger.info(f"Saving new Parquet file to {F_PATH}...")
        await asyncio.to_thread(df.to_parquet, path=F_PATH, index=False)
        logger.info(f"Successfully saved new data to {F_PATH}.")
    except Exception as e:
        logger.error(f"Failed to serialize or save new Parquet file: {e}", exc_info=True)
        raise


@task(retries=3, retry_delay_seconds=5)
async def archive_local_file_to_s3():
    """
    upload parquet file to s3 storage using a client wrapper
    """
    file_exists = await asyncio.to_thread(os.path.exists, F_PATH)
    if not file_exists:
        logger.warning(f"Missing file at {F_PATH}. Skipping upload")
        return

    curr_datetime = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    s3_filename = f"publicMatches_{curr_datetime}.parquet"
    s3_object_key = f"{S3_OBJECT_PREFIX}{s3_filename}"

    try:
        s3_client = S3Wrapper()
        # s3 client is not async, use asyncio.to_thread

        await asyncio.to_thread(s3_client.upload_file, file_path=str(F_PATH), object_key=s3_object_key)

        logger.info(f"{F_PATH} successfully uploaded to S3 at {s3_object_key}")
        logger.info(f"Deleting archived local file: {F_PATH}")
        await asyncio.to_thread(os.remove, F_PATH)

    except Exception as e:
        logger.error(f"Unable to upload {s3_filename} to {s3_object_key}, {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(public_match_orchestrator())
