import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlmodel import delete, select

from sqlalchemy.dialects.postgresql import insert as pginsert

from dota_oracle.data_repository.heroes_repository import HeroesRepository
from ....factories.repository_factories import HeroDataTableFactory
from dota_oracle.data_repository.schemas import HeroDataTable
from dota_oracle.utils import get_logger 

from typing import Dict

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope="session")

@pytest_asyncio.fixture(scope='function')
async def hero_repository_test_subject(test_postgres_engine: AsyncEngine) -> HeroesRepository:
    return HeroesRepository(engine=test_postgres_engine)

@pytest_asyncio.fixture(scope='function', autouse=True)
async def clear_heroes_database(test_postgres_engine):
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(HeroDataTable))

    logger.info(f"hero_database set up complete")
    
    yield
    
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(HeroDataTable))
    
    logger.info("test ended, successfully cleared database records")
    
    
@pytest_asyncio.fixture(scope='function')
async def seed_hero_data(test_postgres_engine) -> Dict[int, str]:
    HERO_DATA = [
        HeroDataTableFactory.build(id=1, localized_name='sniper'),
        HeroDataTableFactory.build(id=2, localized_name='pangolider'),
        HeroDataTableFactory.build(id=3, localized_name='dark willow'),
        HeroDataTableFactory.build(id=4, localized_name='spectre'),
        HeroDataTableFactory.build(id=5, localized_name='crystal maiden'),
    ]
    hero_map = {instance.id:instance.localized_name for instance in HERO_DATA}
    
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            session.add_all(HERO_DATA)
                
    logger.info(f"Sucessfully seeded {len(HERO_DATA)} data")
    
    
    
    return hero_map