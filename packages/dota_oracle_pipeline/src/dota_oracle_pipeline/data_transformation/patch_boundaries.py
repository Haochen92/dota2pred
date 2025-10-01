from typing import List, Optional
from datetime import datetime, timezone

from prefect import task
from sqlalchemy import select, or_

from dota_oracle_common.utils import get_logger, load_workspace_env
from dota_oracle_common.postgresql import DatabaseManager
from dota_oracle_common.models.patches import PatchTable

from ..data_extraction.opendota_explorer import find_match_id_by_timestamp


load_workspace_env()
logger = get_logger(__name__)


@task
async def hydrate_patch_boundaries_task() -> int:
    """
    Hydrate start_match_id and end_match_id on PatchTable rows that are missing them.

    - Always resolve start_match_id when missing.
    - Only resolve end_match_id for patches with a non-null end_time (i.e., closed patches).
    - The latest patch (end_time is None) will keep end_match_id as None.

    Returns the number of patches updated.
    """
    session_factory = DatabaseManager.get_session_factory()
    updated = 0

    async with session_factory() as session:
        stmt = select(PatchTable).where(
            or_(PatchTable.start_match_id.is_(None), PatchTable.end_match_id.is_(None))
        )
        res = await session.execute(stmt)
        patches: List[PatchTable] = list(res.scalars().all())

        if not patches:
            logger.info("All patches already have match_id boundaries. Nothing to hydrate.")
            return 0

        for patch in patches:
            start_ts = patch.start_time

            start_mid: Optional[int] = patch.start_match_id
            if start_mid is None:
                start_mid = await find_match_id_by_timestamp(start_ts)

            end_mid: Optional[int] = patch.end_match_id
            if patch.end_time is not None and end_mid is None:
                end_mid = await find_match_id_by_timestamp(patch.end_time)

            if start_mid is None:
                logger.warning(
                    f"Unable to resolve start boundary for patch {patch.patch_number}. Skipping update."
                )
                continue

            patch.start_match_id = int(start_mid)
            if patch.end_time is not None and end_mid is not None:
                patch.end_match_id = int(end_mid)

            session.add(patch)
            await session.commit()
            updated += 1
            logger.info(
                f"Hydrated patch {patch.patch_number}: start_match_id={patch.start_match_id}, end_match_id={patch.end_match_id}"
            )

    return updated

