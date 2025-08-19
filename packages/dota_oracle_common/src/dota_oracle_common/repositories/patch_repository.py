from typing import Optional, List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .base_repository import BaseRepository
from ..models.patches.table import PatchTable
from ..utils.set_logging import get_logger
from datetime import datetime

logger = get_logger(__name__)


class PatchRepository(BaseRepository):
    """
    Repository for accessing patch data.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def store_patch_tables(self, patch_tables: List[PatchTable]) -> None:
        """
        Store PatchTable instances in the database.

        Args:
            patch_tables: List of PatchTable instances to store.

        Raises:
            Exception: If database operation fails
        """
        if not patch_tables:
            logger.warning("No patch table data provided")
            return

        try:
            await self._upsert_data(model_class=PatchTable, instances=patch_tables)
            logger.info(f"Successfully stored {len(patch_tables)} patch records")

        except Exception as e:
            logger.error(f"Error storing patch data: {e}", exc_info=True)
            raise

    async def get_patch_by_number(self, patch_number: str) -> Optional[PatchTable]:
        """
        Retrieves a single patch by its version number.

        Args:
            patch_number: The patch version string (e.g., "7.35").

        Returns:
            A PatchTable instance or None if not found.

        Raises:
            Exception: If database query fails
        """
        logger.debug(f"Fetching patch details for patch number: {patch_number}")
        try:
            stmt = select(PatchTable).where(PatchTable.patch_number == patch_number)  # type: ignore
            result = await self.session.execute(stmt)
            patch = result.scalar_one_or_none()
            if not patch:
                logger.warning(f"No patch found for number: {patch_number}")
            return patch
        except Exception as e:
            logger.error(f"Error fetching patch by number '{patch_number}': {e}", exc_info=True)
            raise

    async def get_patch_mapping(self) -> Dict[str, datetime]:
        """
        Retrieves a mapping of patch numbers to their start times.

        Returns:
            Dictionary mapping patch numbers to datetime objects.

        Raises:
            Exception: If database query fails
        """
        try:
            stmt = select(PatchTable.patch_number, PatchTable.start_time)  # type: ignore
            result = await self.session.execute(stmt)
            rows = result.mappings().all()

            if not rows:
                logger.warning("No patch mapping data found")
                return {}

            patch_mapping: Dict[str, datetime] = {row["patch_number"]: row["start_time"] for row in rows}

            logger.info(f"Retrieved patch mapping for {len(patch_mapping)} patches")
            return patch_mapping

        except Exception as e:
            logger.error(f"Error retrieving patch mapping: {e}", exc_info=True)
            raise
