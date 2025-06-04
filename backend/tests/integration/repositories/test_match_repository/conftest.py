import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from ....factories.repository_factories import MatchOutcomeTableFactory, MatchTableFactory
from dota_oracle.models.match import MatchOutcomeTable, MatchTable
from dota_oracle.data_repository.match_repository import MatchRepository


from typing import Tuple, AsyncGenerator, Dict

from dota_oracle.utils.set_logging import get_logger

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session')


# ========================
# FIXTURES
# ========================

@pytest_asyncio.fixture(scope='function')
async def match_repository_test_subject(db_session: AsyncSession):
    return MatchRepository(session=db_session)


@pytest_asyncio.fixture(scope='function')
async def seed_test_data(db_session: AsyncSession) -> AsyncGenerator[Tuple[Dict[int, MatchTable], Dict[int, MatchOutcomeTable]], None]:
    """Seed database with partial data for testing joins."""
    match_instance_ids = [1001, 1002, 1003, 1004, 1005, 1006]  # 5 matches with details
    match_outcome_ids = [1001, 1002, 1003, 1004]         # 4 matches with outcomes
    
    match_instances = [MatchTableFactory.build(match_id=match_id) for match_id in match_instance_ids]
    match_outcome_instances = [MatchOutcomeTableFactory.build(match_id=match_id) for match_id in match_outcome_ids]
    
    match_dict = {instance.match_id: instance for instance in match_instances}
    match_outcome_dict = {instance.match_id: instance for instance in match_outcome_instances}
    

    db_session.add_all(match_instances + match_outcome_instances)
    await db_session.flush()
    
    logger.info(f"Seeded {len(match_instances)} match details and {len(match_outcome_instances)} outcomes")
    
    yield (match_dict, match_outcome_dict)
