from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from .schemas.inference import MatchPredictionTable
from sqlalchemy.dialects.postgresql import insert
from dota_oracle.utils.set_logging import get_logger
from .base_repository import BaseRepository
from typing import Optional, List
from sqlmodel import select
from sqlalchemy.exc import SQLAlchemyError

logger = get_logger(__name__)

class PredictionRepository(BaseRepository):
    """
    Repository for storing and retrieving match predictions.
    Returns SQLModel instances or lists thereof.
    """
    def __init__(self, engine: AsyncEngine):
        super().__init__(engine=engine)

    async def store_match_prediction(self, match_prediction: MatchPredictionTable) -> None:
        """
        Stores or updates a match prediction using INSERT ... ON CONFLICT DO UPDATE.
        """
        match_id = match_prediction.match_id
        predictor_name = match_prediction.predictor_name
        predictor_version = match_prediction.predictor_version
        logger.info(f"Storing prediction for match: {match_id}, "
                     f"model: {predictor_name}, v:{predictor_version}")
        
        pk_fields = [col.name for col in MatchPredictionTable.__table__.primary_key.columns]
        primary_keys = set(pk_fields)
        
        upsert_cols = {
            col.name: insert(MatchPredictionTable).excluded[col.name]
            for col in MatchPredictionTable.__table__.columns
            if col.name not in primary_keys
        }
        
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                try:
                    insert_dict = match_prediction.model_dump()
                    stmt = insert(MatchPredictionTable).values(insert_dict).on_conflict_do_update(
                        index_elements=pk_fields,
                        set_=upsert_cols
                    )

                    await session.execute(stmt)
                    logger.info(f"Successfully stored/updated prediction for match {match_id} by {predictor_name}.")

                except SQLAlchemyError as e:
                    logger.error(f"DB error storing prediction for match {match_id} by {predictor_name}: {e}", exc_info=True)
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error storing prediction for match {match_id} by {predictor_name}: {e}", exc_info=True)
                    raise

    async def get_specific_prediction_by_model_name(
        self,
        match_id: int,
        predictor_name: str
    ) -> Optional[MatchPredictionTable]:
        """
        Retrieves a specific prediction model instance.

        Returns:
            An optional MatchPredictionTable instance, or None if not found.
        """
        logger.debug(f"Fetching prediction for match {match_id} by {predictor_name}")
        async with AsyncSession(self.engine) as session:
            try:
                stmt = select(MatchPredictionTable).where(
                    MatchPredictionTable.match_id == match_id,
                    MatchPredictionTable.predictor_name == predictor_name
                )
                result = await session.execute(stmt)
                prediction_instance: Optional[MatchPredictionTable] = result.scalars().first()

                if prediction_instance:
                    logger.debug(f"Retrieved prediction instance for match {match_id} by {predictor_name}")
                    return prediction_instance
                else:
                    logger.debug(f"No prediction found for match {match_id} by {predictor_name}")
                    return None
            except SQLAlchemyError as e:
                logger.error(f"DB error retrieving prediction for match {match_id} by {predictor_name}: {e}", exc_info=True)
                raise 
            except Exception as e:
                logger.error(f"Unexpected error retrieving prediction for match {match_id} by {predictor_name}: {e}", exc_info=True)
                raise

    async def get_predictions_for_match_all_models(self, match_id: int) -> List[MatchPredictionTable]:
        """
        Retrieves all prediction model instances for a given match_id.

        Returns:
            A list of MatchPredictionTable instances (potentially empty).
        """
        logger.debug(f"Fetching all predictions for match {match_id}")
        async with AsyncSession(self.engine) as session:
            try:
                stmt = select(MatchPredictionTable).where(MatchPredictionTable.match_id == match_id)
                result = await session.execute(stmt)
                prediction_instances: List[MatchPredictionTable] = list(result.scalars().all())
                logger.debug(f"Retrieved {len(prediction_instances)} prediction instances for match {match_id}")
                return prediction_instances
            except SQLAlchemyError as e:
                logger.error(f"DB error retrieving predictions for match {match_id}: {e}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Unexpected error retrieving predictions for match {match_id}: {e}", exc_info=True)
                raise


    async def get_all_match_predictions(self) -> List[MatchPredictionTable]:
        """
        Retrieves all prediction model instances from the table.

        Returns:
            A list of MatchPredictionTable instances (potentially empty).
        """
        logger.debug("Fetching all predictions")
        async with AsyncSession(self.engine) as session:
            try:
                stmt = select(MatchPredictionTable)
                result = await session.execute(stmt)
                all_predictions: List[MatchPredictionTable] = list(result.scalars().all())
                logger.debug(f"Retrieved {len(all_predictions)} total prediction instances.")
                return all_predictions
            except SQLAlchemyError as e:
                logger.error(f"DB error retrieving all predictions: {e}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Unexpected error retrieving all predictions: {e}", exc_info=True)
                raise


    async def get_predictions_by_predictor(
        self,
        predictor_name: str
    ) -> List[MatchPredictionTable]:
        """
        Retrieves all prediction model instances made by a specific predictor.

        Returns:
            A list of MatchPredictionTable instances (potentially empty).
        """
        logger.debug(f"Fetching all predictions by predictor '{predictor_name}'")
        async with AsyncSession(self.engine) as session:
            try:
                stmt = select(MatchPredictionTable).where(
                    MatchPredictionTable.predictor_name == predictor_name
                )
                result = await session.execute(stmt)
                predictor_predictions: List[MatchPredictionTable] = list(result.scalars().all())
                logger.debug(f"Retrieved {len(predictor_predictions)} prediction instances by predictor '{predictor_name}'")
                return predictor_predictions
            except SQLAlchemyError as e:
                logger.error(f"DB error retrieving predictions by predictor '{predictor_name}': {e}", exc_info=True)
                raise
            except Exception as e:
                logger.error(f"Unexpected error retrieving predictions by predictor '{predictor_name}': {e}", exc_info=True)
                raise