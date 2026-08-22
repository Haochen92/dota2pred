from prefect import flow
from dota_oracle_common.postgresql import database_session_factory_resource
from dota_oracle_common.utils import get_logger
from dota_oracle_common.repositories.patch_repository import PatchRepository
from dota_oracle_common.models.patches import DotaPatch
from dota_oracle_pipeline.data_extraction.fetch_patch_data import fetch_patch_data
from dota_oracle_pipeline.data_transformation.patch_parser import calculate_patch_end_times
from dota_oracle_pipeline.data_transformation import hydrate_patch_boundaries_task
from pydantic import ValidationError
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


@flow
async def patch_data_orchestrator():
    """
    Prefect flow to fetch, parse, and store patch data.
    """
    async with database_session_factory_resource() as session_factory:
        # Fetch patch data from API endpoint
        patch_data = await fetch_patch_data()

        # Store data
        async with session_factory() as session:
            async with session.begin():
                try:
                    await store_patch_data(session, patch_data)
                except Exception as e:
                    raise e

        # Hydrate match_id boundaries (start_match_id for all, end_match_id only for closed patches)
        try:
            updated = await hydrate_patch_boundaries_task(session_factory)
            logger.info(f"Hydrated match_id boundaries for {updated} patches")
        except Exception as e:
            logger.error(f"Failed to hydrate patch boundaries: {e}", exc_info=True)
            raise

    logger.info("Successfully updated patch data and hydrated boundaries")


async def store_patch_data(session: AsyncSession, patch_data: List[DotaPatch]) -> None:
    """
    Parse and store patch data with calculated end times.

    Args:
        session: Database session
        patch_data: List of DotaPatch instances from API
    """
    if not patch_data:
        logger.warning("No patch data provided")
        return

    try:
        # Parse patch data to calculate end times
        patch_tables = calculate_patch_end_times(patch_data)

        # Store in database
        patch_repo = PatchRepository(session)
        await patch_repo.store_patch_tables(patch_tables)

        logger.info(f"Successfully processed and stored {len(patch_tables)} patches")

    except ValidationError as e:
        logger.error(f"Validation error for patch data: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error encountered while storing patch data: {e}", exc_info=True)
        raise
