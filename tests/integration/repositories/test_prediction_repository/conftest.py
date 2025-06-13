import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlmodel import delete
from dota_oracle_common.models.inference import MatchPredictionTable
from dota_oracle_common.repositories.prediction_repository import PredictionRepository

from dota_oracle_common.utils.set_logging import get_logger

from typing import List

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture(scope='function')
async def prediction_repository_test_subject(db_session: AsyncSession):
    return PredictionRepository(db_session)

    
@pytest_asyncio.fixture(scope='function')
async def seed_prediction_data(db_session, match_table_factory, match_prediction_table_factory) -> List[MatchPredictionTable]:
    
    match_ids = [i for i in range(1001, 1010)] # seed 9 datapoints
    match_data = [match_table_factory.build(match_id=id) for id in match_ids]
    
    prediction_data = [
        match_prediction_table_factory.build(match_id=1001, predictor_name='random_forest'),
        match_prediction_table_factory.build(match_id=1001, predictor_name='xg_boost'), # Same match, different model
        match_prediction_table_factory.build(match_id=1002, predictor_name='random_forest'),
        match_prediction_table_factory.build(match_id=1003, predictor_name='random_forest'),
    ]
    
    db_session.add_all(match_data + prediction_data)
            
    await db_session.flush()
    logger.info(f"prediction data seeding completed - inserted {len(prediction_data)} records")
    
    return prediction_data

@pytest_asyncio.fixture(scope='function')
async def prediction_db_fetcher(db_session:AsyncSession):
    return PredictorFetcherClass(session=db_session)


class PredictorFetcherClass:
    def __init__(self, session: AsyncSession): # Corrected constructor name
        self.session = session

    async def fetch_prediction_data(self, match_id: int, predictor_name: str): # Add return type hint
        stmt = select(MatchPredictionTable).where(
            MatchPredictionTable.match_id == match_id,
            MatchPredictionTable.predictor_name == predictor_name,
        )

        # Execute the statement and get the result
        result = await self.session.execute(stmt.execution_options(populate_existing=True)) # Added await
        
        # If you intend to get the actual data:
        prediction_instance = result.scalar_one_or_none() 

        await self.session.flush() 

        return prediction_instance 
    