from datetime import datetime, timezone # Added timezone
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from .schemas.inference import MatchPredictionTable
from sqlalchemy.dialects.postgresql import insert
from utils.set_logging import get_logger
from .base_repository import BaseRepository
from typing import Optional
from sqlmodel import select
import pandas as pd

logger = get_logger(__name__)

class PredictionRepository(BaseRepository):
    def __init__(self, engine: AsyncEngine):
        super().__init__(engine=engine)

    async def store_match_prediction(
        self,
        match_id: int,
        prediction: bool,
        predictor_name: str, 
        predictor_version: str, 
        prediction_probability: Optional[float] = None
    ) -> None: 

        async with AsyncSession(self.engine) as session:
            try:
                # Define the values to insert
                insert_values = {
                    'match_id': match_id,
                    'prediction': prediction,
                    'predictor_name': predictor_name,
                    'predictor_version': predictor_version,
                    'prediction_timestamp': datetime.now(timezone.utc),
                    'prediction_probability': prediction_probability
                }

                update_columns = {
                    'prediction': insert(MatchPredictionTable).excluded.prediction,
                    'predictor_version': insert(MatchPredictionTable).excluded.predictor_version,
                    'prediction_timestamp': insert(MatchPredictionTable).excluded.prediction_timestamp,
                    'prediction_probability': insert(MatchPredictionTable).excluded.prediction_probability
                }

                stmt = insert(MatchPredictionTable).values(insert_values).on_conflict_do_update(
                    index_elements=['match_id', 'predictor_name'],
                    set_=update_columns
                )

                await session.execute(stmt)
                await session.commit()
                logger.info(f"Successfully stored/updated prediction for match {match_id} by {predictor_name}.")

            except Exception as e:
                await session.rollback()
                logger.error(f"Error storing prediction for match {match_id} by {predictor_name}: {e}", exc_info=True)
                raise e 
    async def get_specific_prediction(
        self,
        match_id: int,
        predictor_name: str
    ) -> pd.DataFrame:
        """
        Retrieves a specific prediction using mappings().
        Returns a DataFrame (empty if not found, single row if found).
        """
        async with AsyncSession(self.engine) as session:
            try:
                stmt = select(MatchPredictionTable).where(
                    MatchPredictionTable.match_id == match_id,
                    MatchPredictionTable.predictor_name == predictor_name
                )
                result = await session.execute(stmt)
                row_mapping = result.mappings().first()

                if row_mapping:
                    logger.debug(f"Retrieved prediction mapping for match {match_id} by {predictor_name}")
                    return pd.DataFrame([dict(row_mapping)]) 
                else:
                    logger.debug(f"No prediction found for match {match_id} by {predictor_name}")
                    return pd.DataFrame()
            except Exception as e:
                logger.error(f"Error retrieving prediction mapping for match {match_id} by {predictor_name}: {e}", exc_info=True)
                raise e

    async def get_predictions_for_match(self, match_id: int) -> pd.DataFrame:
        """
        Retrieves all predictions for a match using mappings().
        Returns a DataFrame (potentially empty).
        """
        async with AsyncSession(self.engine) as session:
            try:
                stmt = select(MatchPredictionTable).where(MatchPredictionTable.match_id == match_id)
                result = await session.execute(stmt)
                row_mappings = result.mappings().all()
                logger.debug(f"Retrieved {len(row_mappings)} prediction mappings for match {match_id}")

                return pd.DataFrame([dict(row) for row in row_mappings])
            except Exception as e:
                logger.error(f"Error retrieving prediction mappings for match {match_id}: {e}", exc_info=True)
                raise e

    async def get_all_match_predictions(self) -> pd.DataFrame:
        """
        Retrieves all predictions using mappings().
        Returns a DataFrame (potentially empty).
        """
        async with AsyncSession(self.engine) as session:
            try:
                stmt = select(MatchPredictionTable)
                result = await session.execute(stmt)
                row_mappings = result.mappings().all()
                logger.debug(f"Retrieved {len(row_mappings)} total prediction mappings.")

                # Directly create DataFrame
                return pd.DataFrame([dict(row) for row in row_mappings])
            except Exception as e:
                logger.error(f"Error retrieving all prediction mappings: {e}", exc_info=True)
                raise e


    async def get_predictions_by_predictor(
        self,
        predictor_name: str
    ) -> pd.DataFrame:
        """
        Retrieves all predictions by predictor using mappings().
        Returns a DataFrame (potentially empty).
        """
        async with AsyncSession(self.engine) as session:
            try:
                stmt = select(MatchPredictionTable).where(
                    MatchPredictionTable.predictor_name == predictor_name
                )
                result = await session.execute(stmt)
                row_mappings = result.mappings().all()
                logger.debug(f"Retrieved {len(row_mappings)} prediction mappings by predictor '{predictor_name}'")

                return pd.DataFrame([dict(row) for row in row_mappings])
            except Exception as e:
                logger.error(f"Error retrieving prediction mappings by predictor '{predictor_name}': {e}", exc_info=True)
                raise e