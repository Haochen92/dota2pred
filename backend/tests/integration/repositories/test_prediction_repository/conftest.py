import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import delete, select

from ....factories.repository_factories import MatchPredictionTableFactory
from dota_oracle.data_repository.schemas import MatchPredictionTable
from dota_oracle.data_repository.prediction_repository import PredictionRepository

from typing import List, Tuple, Any, AsyncGenerator, Dict, Set

from dota_oracle.utils.set_logging import get_logger

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session')


@pytest_asyncio.fixture(scope='function')
async def prediction_repository_test_subject(test_postgres_engine: AsyncEngine):
    return PredictionRepository(test_postgres_engine)


@pytest_asyncio.fixture(scope='function', autouse=True)
async def setup_and_clear_table(test_postgres_engine):
    
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(MatchPredictionTable))
            
    logger.info(f"cleared database, test setup complete")
    
    yield
    
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(MatchPredictionTable))
            
    logger.info(f"test completed, database cleared successfully") 
    
    
@pytest_asyncio.fixture(scope='function')
async def seed_prediction_data(test_postgres_engine) -> List[MatchPredictionTable]:
    prediction_data = [
        MatchPredictionTableFactory.build(match_id=1001, predictor_name='random_forest'),
        MatchPredictionTableFactory.build(match_id=1001, predictor_name='xg_boost'), # Same match, different model
        MatchPredictionTableFactory.build(match_id=1002, predictor_name='random_forest'),
        MatchPredictionTableFactory.build(match_id=1003, predictor_name='random_forest'),
    ]
    
    seeded_data = prediction_data.copy()
    
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            session.add_all(prediction_data)
            
    logger.info(f"prediction data seeding completed")
    
    return seeded_data