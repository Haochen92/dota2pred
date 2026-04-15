from typing import List, Optional
from ..models.match import MatchOutcomeTable, MatchTable, MatchWithOutcome
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from ..utils.set_logging import get_logger
from .base_repository import BaseRepository
from pydantic import ValidationError

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
        if not instances:  # Good practice to check for empty list early
            logger.debug("No MatchTable instances provided for insert_match_details.")
            return

        logger.debug(f"Attempting to insert {len(instances)} MatchTable data")

        try:
            await self._insert_data(model_class=MatchTable, instances=instances)
        except Exception as e:
            logger.error(f"Error encountered when trying to insert MatchTable data, {e}", exc_info=True)
            raise

    async def insert_match_outcome(self, instances: List[MatchOutcomeTable]) -> None:
        """
        args: instances: A list of MatchOutcomeTable Instances

        Description:
        Insert a match outcome using INSERT ... ON CONFLICT DO UPDATE.
        """
        if not instances:
            logger.debug("No MatchOutcomeTable instances provided for insert_match_outcome.")
            return

        logger.info(f"Attempting to insert {len(instances)} instances to MatchOutcomeTable")

        try:
            await self._insert_data(model_class=MatchOutcomeTable, instances=instances)
        except Exception as e:
            logger.error(f"Error encountered when trying to insert MatchTable data, {e}", exc_info=True)
            raise

    async def insert_match_with_outcome(self, instances: List[MatchWithOutcome]) -> None:
        """
        args: instances: A list of MatchWithOutcome DTO

        Description:
            Store completed match into MatchTable and MatchOutcomeTable using cascade.
            No conflict handling feature.
        """

        validated_matches = []
        # Validate Inputs
        for match in instances:
            try:
                validated_match = MatchTable.model_validate(match)
                validated_match.outcome = MatchOutcomeTable.model_validate(match)
                validated_matches.append(validated_match)
            except (ValueError, ValidationError) as ve:
                logger.warning(f"Match match_id: {match.match_id} failed validation, {ve}")
                continue

        if not validated_matches:
            logger.info("No validated matches, returning...")
            return

        try:
            self.session.add_all(validated_matches)
        except SQLAlchemyError as e:
            logger.error(f"Database error encountered when attempting to insert data {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error while inserting data: {e}", exc_info=True)
            raise

    async def upsert_match_with_outcome(self, instances: List[MatchWithOutcome]) -> None:
        """
        Takes a list of MatchWithOutcome DTOs and upserts them into their
        respective tables (MatchTable and MatchOutcomeTable).

        This method does NOT use ORM cascades. Instead, it prepares two separate
        lists of validated models and calls the generic _upsert_data method for each,
        ensuring an efficient bulk INSERT...ON CONFLICT DO UPDATE operation.
        """
        match_details_instances: List[MatchTable] = []
        match_outcome_instances: List[MatchOutcomeTable] = []

        # Step 1: Validate and split the DTOs into two separate lists of models
        for match_dto in instances:
            try:
                # Validate against both target models
                match_details_instances.append(MatchTable.model_validate(match_dto))
                match_outcome_instances.append(MatchOutcomeTable.model_validate(match_dto))
            except (ValidationError, ValueError) as ve:
                logger.warning(f"A DTO for match {match_dto.match_id} failed validation and will be skipped: {ve}")
                continue

        if not match_details_instances:
            logger.info("No valid matches to upsert after validation.")
            return

        try:
            # Step 2: Call the generic upsert method for each table
            logger.info(f"Upserting {len(match_details_instances)} records into MatchTable...")
            await self._upsert_data(model_class=MatchTable, instances=match_details_instances)

            logger.info(f"Upserting {len(match_outcome_instances)} records into MatchOutcomeTable...")
            await self._upsert_data(model_class=MatchOutcomeTable, instances=match_outcome_instances)

            logger.info("Successfully completed upsert operations for both tables.")

        except Exception as e:
            logger.error(f"An error occurred during the two-step upsert process: {e}", exc_info=True)
            raise

    async def get_match_details(
        self,
        *,
        input_id_list: Optional[List[int]] = [],
        relationship_fields: Optional[List[str]] = None,
        limit: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> List[MatchTable]:
        """
        Retrieves a list of match_details with optional relationships and time range filtering.

        Args:
            input_id_list: Optional list of match IDs to filter by
            relationship_fields: Optional list of relationship names to eagerly load
            limit: Optional limit on number of results
            start_time: Optional start time (inclusive) for time range filtering
            end_time: Optional end time (exclusive) for time range filtering

        Returns:
            List of MatchTable instances matching the criteria
        """
        logger.debug(
            f"Fetching MatchTable details. IDs: {input_id_list}, Relationships: {relationship_fields}, Limit: {limit}, "
            f"Start time: {start_time}, End time: {end_time}"
        )

        try:
            match_details_list = await self._get_data(
                model_class=MatchTable,
                id_filters=input_id_list,
                relationships=relationship_fields,
                limit=limit,
                start_time=start_time,
                end_time=end_time,
            )

            if not match_details_list:
                logger.debug(
                    f"No MatchTable details found for IDs: {input_id_list if input_id_list else 'all'} "
                    f"with limit: {limit}."
                )
                return []  # Return empty list for "not found"
            logger.info(f"Found {len(match_details_list)} MatchTable details.")
            return match_details_list
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching match details: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching details/outcome for match_details {e}", exc_info=True)
            raise
