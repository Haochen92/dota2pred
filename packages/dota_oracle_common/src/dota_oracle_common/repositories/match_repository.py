from typing import List, Optional
from ..models.match import MatchOutcomeTable, MatchTable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from ..utils.set_logging import get_logger
from .base_repository import BaseRepository

logger = get_logger(__name__)

class MatchRepository(BaseRepository):
    """
    Repository for accessing and storing match details and outcomes.
    Returns SQLModel instances or lists/tuples thereof.
    """
    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def insert_match_details(self, instances: List[MatchTable]) -> None:
        """
        Inserts match details from a MatchTable Instance.
        Uses INSERT ... ON CONFLICT DO NOTHING.
        """      
        if not instances: # Good practice to check for empty list early
            logger.debug("No MatchTable instances provided for insert_match_details.")
            return
        
        logger.debug(f"Attempting to insert {len(instances)} MatchTable data")
        
        try:
            await self._insert_data(
                model_class=MatchTable,
                instances=instances
            )
        except Exception as e:
            logger.error(f"Error encountered when trying to insert MatchTable data, {e}", exc_info=True)
            raise

    async def insert_match_outcome(self, instances: List[MatchOutcomeTable]) -> None:
        """
        Upsert a match outcome using INSERT ... ON CONFLICT DO UPDATE.
        """
        if not instances:
            logger.debug("No MatchOutcomeTable instances provided for insert_match_outcome.")
            return
        
        logger.info(f"Attempting to insert {len(instances)} instances to MatchOutcomeTable")
        
        try:
            await self._insert_data(
                model_class=MatchOutcomeTable,
                instances=instances
            )
        except Exception as e:
            logger.error(f"Error encountered when trying to insert MatchTable data, {e}", exc_info=True)
            raise

    async def get_match_details(
        self,
        *,
        input_id_list: Optional[List[int]] = [],
        relationship_fields: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[MatchTable]:
        """
            Retrieves a list of match_details with optional relationships if any
        """
        logger.debug(
            f"Fetching MatchTable details. IDs: {input_id_list}, Relationships: {relationship_fields}, Limit: {limit}"
        )
        
        try:
            match_details_list = await self._get_data(
                model_class=MatchTable,
                id_filters=input_id_list,
                relationships=relationship_fields,
                limit=limit
            )
            
            if not match_details_list:
                logger.debug(
                    f"No MatchTable details found for IDs: {input_id_list if input_id_list else 'all'} "
                    f"with limit: {limit}."
                )
                return [] # Return empty list for "not found"
            logger.info(f"Found {len(match_details_list)} MatchTable details.")
            return match_details_list # type: ignore
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching match details: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching details/outcome for match_details {e}", exc_info=True)
            raise 
        
    