from typing import List, Optional, Dict, Any, Tuple
from .schemas.matches import MatchTable, MatchOutcomeTable
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from utils.set_logging import get_logger
from pydantic_models.match import Match as MatchPydantic
from .base_repository import BaseRepository
import asyncio

logger = get_logger(__name__)

MatchWithOutcome = Tuple[MatchTable, MatchOutcomeTable]

class MatchRepository(BaseRepository):
    """
    Repository for accessing and storing match details and outcomes.
    Returns SQLModel instances or lists/tuples thereof.
    """
    def __init__(self, engine: AsyncEngine):
        super().__init__(engine=engine)
        self.match_table_cols = {c.name for c in MatchTable.__table__.columns}
        self.outcome_table_cols = {c.name for c in MatchOutcomeTable.__table__.columns}
        # Defensive check for match_id to be present
        if 'match_id' not in self.match_table_cols or 'match_id' not in self.outcome_table_cols:
             logger.warning("MatchRepository initialized but 'match_id' missing from MatchTable or MatchOutcomeTable columns.")


    async def insert_match_details(self, match_data: Dict[str, Any]) -> None:
        """
        Inserts match details from a dictionary, filtering keys to match MatchTable columns.
        Uses INSERT ... ON CONFLICT DO NOTHING.
        """
        match_id = match_data.get('match_id', 'UNKNOWN')
        logger.debug(f"Attempting to insert details for match {match_id}")
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                try:
                    # Filter input dict to only include keys present in the MatchTable schema
                    match_db_dict = {k: v for k, v in match_data.items() if k in self.match_table_cols}
                    if 'match_id' not in match_db_dict:
                        raise ValueError(f"Cannot insert match details: 'match_id' missing from input data.")

                    stmt = insert(MatchTable).values(match_db_dict).on_conflict_do_nothing(
                        index_elements=['match_id']
                    )
                    await session.execute(stmt)
                    logger.info(f"Insert details statement executed for match {match_id}")
                except SQLAlchemyError as e:
                    logger.error(f"DB error inserting details for match {match_id}: {e}", exc_info=True)
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error inserting details for match {match_id}: {e}", exc_info=True)
                    raise

    async def insert_match_outcome(self, match_id: int, outcome: bool) -> None:
        """
        Inserts or updates a match outcome using INSERT ... ON CONFLICT DO UPDATE.
        """
        logger.debug(f"Attempting to insert/update outcome for match {match_id}")
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                try:
                    outcome_db_dict = {'match_id': match_id, 'radiant_win': outcome}
                    valid_outcome_dict = {k:v for k,v in outcome_db_dict.items() if k in self.outcome_table_cols}
                    if 'match_id' not in valid_outcome_dict:
                         raise ValueError(f"Cannot insert match outcome: 'match_id' key missing internally.")

                    stmt = insert(MatchOutcomeTable).values(valid_outcome_dict).on_conflict_do_update(
                        index_elements=["match_id"],
                        set_={
                            'radiant_win': insert(MatchOutcomeTable).excluded.radiant_win
                        }
                    )
                    await session.execute(stmt)
                    logger.info(f"Insert/update outcome statement executed for match {match_id}")
                except SQLAlchemyError as e:
                    logger.error(f"DB error inserting outcome for match {match_id}: {e}", exc_info=True)
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error inserting outcome for match {match_id}: {e}", exc_info=True)
                    raise

    async def add_matches_with_outcome_batch(self, matches: List[MatchPydantic]) -> None:
        """
        Adds a batch of matches and their outcomes. Uses ON CONFLICT clauses.
        Accepts a list of Pydantic Match models.
        """
        if not matches:
            logger.warning("No matches provided for batch insert with outcome.")
            return

        match_db_dicts = []
        outcome_db_dicts = []

        for match in matches:
            match_full_dict = match.model_dump()
            match_data = {k: v for k, v in match_full_dict.items() if k in self.match_table_cols}
            outcome_data = { k: v for k, v in match_full_dict.items() if k in self.outcome_table_cols }
            
            if 'match_id' in match_data:
                 match_db_dicts.append(match_data)
            if 'match_id' in outcome_data and 'radiant_win' in outcome_data:
                 outcome_db_dicts.append(outcome_data)

        if not match_db_dicts or not outcome_db_dicts:
             logger.warning("Filtered match data resulted in empty lists for DB insert.")
             return

        async with AsyncSession(self.engine) as session:
            async with session.begin():
                try:
                    if match_db_dicts:
                        match_stmt = insert(MatchTable).values(match_db_dicts).on_conflict_do_nothing(
                            index_elements=["match_id"]
                        )
                        await session.execute(match_stmt)

                    if outcome_db_dicts:
                        outcome_stmt = insert(MatchOutcomeTable).values(outcome_db_dicts).on_conflict_do_update(
                            index_elements=["match_id"],
                            set_={
                                "radiant_win": insert(MatchOutcomeTable).excluded.radiant_win,
                            }
                        )
                        await session.execute(outcome_stmt)

                    logger.info(f"Batch insert/update executed for {len(matches)} input matches.")

                except SQLAlchemyError as e:
                    logger.error(f"DB error during batch insert of matches/outcomes: {e}", exc_info=True)
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error during batch insert of matches/outcomes: {e}", exc_info=True)
                    raise

    async def get_match_details_with_outcome(self, match_id: int) -> Optional[MatchWithOutcome]:
        """
        Retrieves both MatchTable and MatchOutcomeTable instances for a given match_id.

        Returns:
            An optional tuple (MatchTable, MatchOutcomeTable), or None if either part is missing.
        """
        logger.debug(f"Fetching details and outcome for match {match_id}")
        try:
            # Fetch both parts concurrently using asyncio.gather for potential slight speedup
            match_details_task = self._get_instance_by_id(MatchTable, match_id)
            match_outcome_task = self._get_instance_by_id(MatchOutcomeTable, match_id)

            match_details, match_outcome = await asyncio.gather(match_details_task, match_outcome_task)

            if match_details and match_outcome:
                logger.debug(f"Found both details and outcome for match {match_id}")
                return match_details, match_outcome
            else:
                logger.warning(f"Could not find both details and outcome for match {match_id}. Details found: {match_details is not None}, Outcome found: {match_outcome is not None}")
                return None
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching details/outcome for match {match_id}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching details/outcome for match {match_id}: {e}", exc_info=True)
            raise 


    async def get_match_details(self, match_id: int) -> Optional[MatchTable]:
        """Retrieves a single MatchTable instance by match_id."""
        logger.debug(f"Fetching details for match {match_id}")
        try:
            match_instance: Optional[MatchTable] = await self._get_instance_by_id(MatchTable, match_id)
            if not match_instance:
                logger.debug(f"No details found for match {match_id}")
                return None
            logger.debug(f"Found details for match {match_id}")
            return match_instance
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching details for match {match_id}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching details for match {match_id}: {e}", exc_info=True)
            raise

    async def get_match_details_batch(self, list_match_ids: List[int]) -> List[MatchTable]:
        """Retrieves multiple MatchTable instances by a list of match_ids."""
        if not list_match_ids:
            return []
        logger.debug(f"Fetching details batch for {len(list_match_ids)} matches.")
        try:
            match_instances: List[MatchTable] = await self._get_instances_by_batch_ids(MatchTable, list_match_ids)
            logger.debug(f"Found {len(match_instances)} details in batch.")
            return match_instances
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching details batch: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching details batch: {e}", exc_info=True)
            raise


    async def get_match_outcome(self, match_id: int) -> Optional[MatchOutcomeTable]:
        """Retrieves a single MatchOutcomeTable instance by match_id."""
        logger.debug(f"Fetching outcome for match {match_id}")
        try:
            match_outcome_instance: Optional[MatchOutcomeTable] = await self._get_instance_by_id(MatchOutcomeTable, match_id)
            if not match_outcome_instance:
                logger.debug(f"No outcome found for match {match_id}")
                return None
            logger.debug(f"Found outcome for match {match_id}")
            return match_outcome_instance
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching outcome for match {match_id}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching outcome for match {match_id}: {e}", exc_info=True)
            raise


    async def get_match_outcome_batch(self, list_match_ids: List[int]) -> List[MatchOutcomeTable]:
        """Retrieves multiple MatchOutcomeTable instances by a list of match_ids."""
        if not list_match_ids:
            return []
        logger.debug(f"Fetching outcome batch for {len(list_match_ids)} matches.")
        try:
            match_outcome_instances: List[MatchOutcomeTable] = await self._get_instances_by_batch_ids(MatchOutcomeTable, list_match_ids)
            logger.debug(f"Found {len(match_outcome_instances)} outcomes in batch.")
            return match_outcome_instances
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching outcome batch: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching outcome batch: {e}", exc_info=True)
            raise


    async def get_all_match_details(self) -> List[MatchTable]:
        """Retrieves all MatchTable instances."""
        logger.debug("Fetching all match details.")
        try:
            list_match_instances: List[MatchTable] = await self._get_all_data_by_class(MatchTable)
            logger.debug(f"Found {len(list_match_instances)} total match details.")
            return list_match_instances
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching all match details: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching all match details: {e}", exc_info=True)
            raise


    async def get_all_match_outcome(self) -> List[MatchOutcomeTable]:
        """Retrieves all MatchOutcomeTable instances."""
        logger.debug("Fetching all match outcomes.")
        try:
            list_match_outcome: List[MatchOutcomeTable] = await self._get_all_data_by_class(MatchOutcomeTable)
            logger.debug(f"Found {len(list_match_outcome)} total match outcomes.")
            return list_match_outcome
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching all match outcomes: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching all match outcomes: {e}", exc_info=True)
            raise


    async def get_all_match_details_with_outcome(self) -> List[MatchWithOutcome]:
        """
        Retrieves all matches that have both details and outcome recorded.

        Returns:
            A list of tuples, where each tuple is (MatchTable, MatchOutcomeTable).
        """
        logger.debug("Fetching all matches with details and outcome.")
        try:
            # Fetch all details and outcomes concurrently
            details_task = self.get_all_match_details()
            outcomes_task = self.get_all_match_outcome()
            all_details, all_outcomes = await asyncio.gather(details_task, outcomes_task)

            # Create a dictionary of outcomes keyed by match_id for efficient lookup
            outcomes_dict: Dict[int, MatchOutcomeTable] = {outcome.match_id: outcome for outcome in all_outcomes}

            # Combine details with outcomes
            combined_results: List[MatchWithOutcome] = []
            for detail in all_details:
                outcome = outcomes_dict.get(detail.match_id)
                if outcome:
                    combined_results.append((detail, outcome))

            logger.debug(f"Found {len(combined_results)} matches with both details and outcome.")
            return combined_results
        except Exception as e:
            # Errors logged in the called methods, could add specific log here too
            logger.error(f"Error during assembly of all matches with details and outcome: {e}", exc_info=True)
            raise