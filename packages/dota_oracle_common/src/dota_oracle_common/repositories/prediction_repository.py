from sqlalchemy.ext.asyncio import AsyncSession

from ..models.inference import MatchPredictionTable
from ..utils.set_logging import get_logger
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

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    async def store_match_prediction(self, match_prediction: MatchPredictionTable) -> None:
        """
        Stores or updates a match prediction using INSERT ... ON CONFLICT DO UPDATE.
        """
        logger.info(f"Atempting to store match_prediction {match_prediction}")

        try:
            await self._upsert_data(model_class=MatchPredictionTable, instances=[match_prediction])

        except Exception as e:
            logger.error(
                f"Error encountered when trying to insert match prediction for match {match_prediction.match_id}"
                f", predictor: {match_prediction.predictor_name}, {e}",
                exc_info=True,
            )

    async def get_prediction_predictor_name_match_id(
        self, match_id: int, predictor_name: str
    ) -> Optional[MatchPredictionTable]:
        """
        Retrieves a specific prediction model instance.

        Returns:
            An optional MatchPredictionTable instance, or None if not found.
        """
        logger.debug(f"Fetching prediction for match {match_id} by {predictor_name}")
        try:
            stmt = select(MatchPredictionTable).where(
                MatchPredictionTable.match_id == match_id, MatchPredictionTable.predictor_name == predictor_name
            )
            result = await self.session.execute(stmt)
            prediction_instance: Optional[MatchPredictionTable] = result.scalars().first()

            if not prediction_instance:
                logger.debug(f"No prediction found for match {match_id} by {predictor_name}")
                return None

            logger.debug(f"Retrieved prediction instance for match {match_id} by {predictor_name}")
            return prediction_instance

        except SQLAlchemyError as e:
            logger.error(f"DB error retrieving prediction for match {match_id} by {predictor_name}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving prediction for match {match_id} by {predictor_name}: {e}", exc_info=True
            )
            raise

    async def get_all_predictions_match_id(self, match_id: int) -> List[MatchPredictionTable]:
        """
        Retrieves all prediction model instances for a given match_id.

        Returns:
            A list of MatchPredictionTable instances (potentially empty).
        """
        logger.debug(f"Fetching all predictions for match {match_id}")

        try:
            stmt = select(MatchPredictionTable).where(MatchPredictionTable.match_id == match_id)
            res = await self.session.execute(stmt.execution_options(populate_existing=True))

            instances = res.scalars().all()
            if not instances:
                logger.debug(f"No predictions found for match_id {match_id}")
                return []
            logger.info(f"found {len(instances)} match predictions")
            return list(instances)
        except Exception as e:
            logger.error(f"Error encountered while fetching data for matches, {match_id}, {e}", exc_info=True)
            raise

    async def get_predictions_by_predictor_name(self, predictor_name: str) -> List[MatchPredictionTable]:
        """
        Retrieves all prediction model instances made by a specific predictor.

        Returns:
            A list of MatchPredictionTable instances (potentially empty).
        """
        logger.debug(f"Fetching all predictions by predictor '{predictor_name}'")
        try:
            stmt = select(MatchPredictionTable).where(MatchPredictionTable.predictor_name == predictor_name)
            result = await self.session.execute(stmt)
            predictor_predictions: List[MatchPredictionTable] = result.scalars().all()  # type: ignore
            logger.debug(f"Retrieved {len(predictor_predictions)} prediction instances by predictor '{predictor_name}'")
            return predictor_predictions
        except SQLAlchemyError as e:
            logger.error(f"DB error retrieving predictions by predictor '{predictor_name}': {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving predictions by predictor '{predictor_name}': {e}", exc_info=True)
            raise
