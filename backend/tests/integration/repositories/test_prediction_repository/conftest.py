import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete

from ....factories.repository_factories import MatchPredictionTableFactory
from dota_oracle.models.inference import MatchPredictionTable
from dota_oracle.data_repository.prediction_repository import PredictionRepository

from dota_oracle.utils.set_logging import get_logger

from typing import List

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session')


@pytest_asyncio.fixture(scope='function')
async def prediction_repository_test_subject(db_session: AsyncSession):
    return PredictionRepository(db_session)

    
@pytest_asyncio.fixture(scope='function')
async def seed_prediction_data(db_session) -> List[MatchPredictionTable]:
    prediction_data = [
        MatchPredictionTableFactory.build(match_id=1001, predictor_name='random_forest'),
        MatchPredictionTableFactory.build(match_id=1001, predictor_name='xg_boost'), # Same match, different model
        MatchPredictionTableFactory.build(match_id=1002, predictor_name='random_forest'),
        MatchPredictionTableFactory.build(match_id=1003, predictor_name='random_forest'),
    ]
    
    db_session.add_all(prediction_data)
            
    await db_session.flush()
    logger.info(f"prediction data seeding completed - inserted {len(prediction_data)} records")
    
    return prediction_data