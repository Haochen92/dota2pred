from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from dota_oracle_common.utils.set_logging import get_logger
from .base_repository import BaseRepository
from ..models.match import PublicMatchTable
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError


logger = get_logger(__name__)


class PublicMatchRepository(BaseRepository):
    """Repository for storing and querying public matches."""

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def insert_public_matches(self, instances: List[PublicMatchTable]) -> None:
        if not instances:
            logger.debug("No PublicMatchTable instances provided for insert_public_matches.")
            return
        await self._insert_data(model_class=PublicMatchTable, instances=instances)

    async def upsert_public_matches(self, instances: List[PublicMatchTable]) -> None:
        if not instances:
            logger.debug("No PublicMatchTable instances provided for upsert_public_matches.")
            return
        await self._upsert_data(model_class=PublicMatchTable, instances=instances)

    async def insert_public_matches_returning_ids(self, instances: List[PublicMatchTable]) -> List[int]:
        """
        Insert a batch of PublicMatchTable rows with ON CONFLICT DO NOTHING, returning the match_ids actually inserted.
        """
        if not instances:
            logger.debug("No PublicMatchTable instances provided for insert_public_matches_returning_ids.")
            return []

        rows = [i.model_dump() for i in instances]
        on_conflict_keys = self._get_primary_key_names(PublicMatchTable)
        stmt = (
            pg_insert(PublicMatchTable) 
            .values(rows)
            .on_conflict_do_nothing(index_elements=on_conflict_keys)
            .returning(PublicMatchTable.match_id) # type: ignore
        )
        result = await self.session.execute(stmt)
        inserted_ids = [r[0] for r in result.fetchall()]
        return inserted_ids

    async def get_public_matches(
        self,
        *,
        input_id_list: Optional[List[int]] = [],
        relationship_fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> List[PublicMatchTable]:
        """
        Retrieves a list of public matches with optional relationships and time range filtering.

        Args:
            input_id_list: Optional list of match IDs to filter by
            relationship_fields: Optional list of relationship names to eagerly load
            limit: Optional limit on number of results
            start_time: Optional start time (inclusive) for time range filtering
            end_time: Optional end time (exclusive) for time range filtering

        Returns:
            List of PublicMatchTable instances matching the criteria
        """

        logger.debug(
            f"Fetching PublicMatchTable entries. IDs: {input_id_list}, Relationships: {relationship_fields}, "
            f"Limit: {limit}, Start time: {start_time}, End time: {end_time}"
        )

        try:
            matches = await self._get_data(
                model_class=PublicMatchTable,
                id_filters=input_id_list,
                relationships=relationship_fields,
                limit=limit,
                start_time=start_time,
                end_time=end_time,
            )

            if not matches:
                logger.debug(
                    f"No PublicMatchTable rows found for IDs: {input_id_list if input_id_list else 'all'} "
                    f"with limit: {limit}."
                )
                return []

            logger.info(f"Found {len(matches)} PublicMatchTable rows.")
            return matches

        except SQLAlchemyError as e:
            logger.error(f"DB error fetching public matches: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching public matches: {e}", exc_info=True)
            raise
