from typing import List, Optional
from .schemas.matches import MatchTable, MatchOutcomeTable
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from utils.set_logging import get_logger
from pydantic_models.match import Match as MatchPydantic
from pydantic import ValidationError
from .base_repository import BaseRepository
import pandas as pd

logger = get_logger(__name__)


class MatchRepository(BaseRepository):
    def __init__(self, engine: AsyncEngine):
        super().__init__(engine=engine)
        self.match_table_cols = set(c.name for c in MatchTable.__table__.columns)
        self.outcome_table_cols = set(c.name for c in MatchOutcomeTable.__table__.columns)

    async def insert_match_details(self, match: MatchPydantic):
        async with AsyncSession(self.engine) as session:
            try:
                match_dict = match.model_dump()
                match_db =  {k : v for k, v in match_dict.items() if k in self.match_table_cols}
                stmt = insert(MatchTable).values(match_db).on_conflict_do_nothing(index_elements=['match_id'])
                await session.execute(stmt)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Error inserting matches into Matches table: {e}", exc_info=True)
                raise e
            

    async def insert_match_outcome(self, match_id: int, outcome: bool):
        async with AsyncSession(self.engine) as session:
            try:  
                outcome_db = {'match_id': match_id, 'radiant_win': outcome}
                stmt = insert(MatchOutcomeTable).values(outcome_db).on_conflict_do_update(
                    index_elements=["match_id"],
                    set_={
                        'radiant_win':insert(MatchOutcomeTable).excluded.radiant_win
                    }
                )
                await session.execute(stmt)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Error inserting matches into Match Outcome table: {e}", exc_info=True)
                raise e
            
    async def add_matches_with_outcome_batch(self, matches: List[MatchPydantic])-> List[int]:
        if not matches:
            logger.info("No matches provided for batch insert.")
            return []

        match_db_dicts = []
        outcome_db_dicts = []
        
        for match in matches:
            match_data = {k : v for k, v in match.model_dump().items() if k in self.match_table_cols}
            outcome_data = {k : v for k, v in match.model_dump().items() if k in self.outcome_table_cols}
            match_db_dicts.append(match_data)
            outcome_db_dicts.append(outcome_data)
            
        async with AsyncSession(self.engine) as session:
            try:
                match_stmt = insert(MatchTable).values(match_db_dicts).on_conflict_do_nothing(
                    index_elements=["match_id"]
                )
                outcome_stmt = insert(MatchOutcomeTable).values(outcome_db_dicts).on_conflict_do_update(
                    index_elements=["match_id"],
                    set_={
                        "radiant_win": insert(MatchOutcomeTable).excluded.radiant_win,
                    }
                )
                await session.execute(match_stmt)
                await session.execute(outcome_stmt)
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Error inserting matches into Match Outcome table: {e}", exc_info=True)
                raise e
            
    async def get_match_details_with_outcome(self, match_id: int) -> pd.DataFrame:
        try:
            match_details: pd.DataFrame = await self.get_match_details(match_id)
            match_outcome: pd.DataFrame = await self.get_match_outcome(match_id)
            if match_details.empty or match_outcome.empty:
                return pd.DataFrame()
            
            match_data =  match_details.merge(match_outcome, on='match_id', how='inner')
            return match_data
        except ValidationError as ve:
            logger.error(f"Validation error for match {match_id}, {ve}", exc_info=True)
            raise ve
        except Exception as e:
            logger.error(f"Error fetching match_details with outcome for match {match_id}, {e}", exc_info=True)
            raise e
            
        
                
    async def get_match_details(self, match_id:int) -> pd.DataFrame:
        try: 
            match_instance: Optional[MatchTable] = await self._get_instance_by_id(MatchTable, match_id)
            if not match_instance:
                return pd.DataFrame()
            return pd.DataFrame([match_instance.model_dump()])
        except Exception as e:
            logger.error(f"Error fetching match_details for match {match_id}: {e}", exc_info=True)
            raise e
        
    async def get_match_outcome(self, match_id:int) -> pd.DataFrame:
        try:
            match_outcome_instance: Optional[MatchOutcomeTable] = await self._get_instance_by_id(MatchOutcomeTable, match_id)
            if not match_outcome_instance:
                return pd.DataFrame()
            return pd.DataFrame([match_outcome_instance.model_dump()])
        except Exception as e:
            logger.error(f"Error fetching match outcome for match {match_id}: {e}", exc_info=True)
            raise e
    
    async def get_all_match_details(self) -> pd.DataFrame:
        try:
            list_match_instances: List[MatchTable] = await self._get_all_data_by_class(MatchTable)
            match_details = pd.DataFrame([instance.model_dump() for instance in list_match_instances])
            return match_details
        except Exception as e:
            logger.error(f"Error fetching match_details from MatchTable: {e}", exc_info=True)
            raise e
        
    
    async def get_all_match_outcome(self) -> pd.DataFrame:
        try:
            list_match_outcome: List[MatchOutcomeTable] = await self._get_all_data_by_class(MatchOutcomeTable)
            match_outcome = pd.DataFrame([instance.model_dump() for instance in list_match_outcome])
            return match_outcome
        except Exception as e:
            logger.error(f"Error fetching match_outcome from MatchOutcomeTable: {e}", exc_info=True)
            raise e
        
        
    async def get_all_match_details_with_outcome(self):
        try:
            match_details: pd.DataFrame = await self.get_all_match_details()
            match_outcomes: pd.DataFrame = await self.get_all_match_outcome()
            final_dataframe = match_details.merge(match_outcomes, on='match_id', how='inner')
            return final_dataframe
        except Exception as e:
            logger.error(f"Error fetching match details with outcome {e}", exc_info=True)
            raise e
            
