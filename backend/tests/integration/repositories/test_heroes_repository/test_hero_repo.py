import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlmodel import delete, select

from sqlalchemy.dialects.postgresql import insert as pginsert

from dota_oracle.data_repository.heroes_repository import HeroesRepository
from ....factories.repository_factories import HeroDataTableFactory
from dota_oracle.data_repository.schemas import HeroDataTable
from dota_oracle.utils import get_logger 

from typing import List


logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope="session")

class TestStoreHeroData:
    
    async def test_store_new_data(
        self,
        hero_repository_test_subject: HeroesRepository,
        test_postgres_engine: AsyncEngine
    ):
        # ARRANGE
        input_data = {
            'anti-mage': HeroDataTableFactory.build(id=10, localized_name='anti-mage'),
            'lina': HeroDataTableFactory.build(id=11, localized_name='lina')
        }
        
        
        # ACT
        
        await hero_repository_test_subject.store_hero_data(input_data) 
        
        stored_heroes = await self._get_instances(test_postgres_engine, [10, 11])
                
        # ASSERT
        assert len(stored_heroes) == len(input_data), f"expected {len(stored_heroes)} data, got {len(input_data)}"
        
        for hero_data in stored_heroes:
            hero_name = hero_data.localized_name
            
            assert hero_name in set(input_data.keys()), f"extracted hero data has different localised name: {hero_name}"
            
            input_instance = input_data[hero_name]
            
            self._assert_equal(hero_data, input_instance)
            
    async def test_update_data_for_existing(
        self,
        hero_repository_test_subject: HeroesRepository,
        test_postgres_engine: AsyncEngine
    ):
        # Arrange
        initial_data = {'Sven': HeroDataTableFactory.build(id=13, localized_name='Sven', base_armor=5.3)}
        
        # Act
        await hero_repository_test_subject.store_hero_data(initial_data)
        
        # Fetch Stored data
        stored_hero_data = await self._get_instances(test_postgres_engine, [13])
        
        # Validate stored data
        
        assert len(stored_hero_data) == len(initial_data), f"expected {len(stored_hero_data)} data, got {len(initial_data)}"
        
        for hero_data in stored_hero_data:
            hero_name = hero_data.localized_name
            
            assert hero_name in set(initial_data.keys()), f"extracted hero data has different localised name: {hero_name}"
            
            input_instance = initial_data[hero_name]
            
            self._assert_equal(hero_data, input_instance)
        
        # Seed again with modified base armour
        
        reinsert_data = {'Sven': HeroDataTableFactory.build(id=13, localized_name='Sven', base_armor=10.6)}
        await hero_repository_test_subject.store_hero_data(reinsert_data)
        
        # Fetch Stored data again
        stored_hero_data = await self._get_instances(test_postgres_engine, [13])
        data_instance = stored_hero_data[0]
        
        # Validate stored data with updated values
        assert data_instance.base_armor == 10.6, f"expected updated data to be {10.6}, got {data_instance.base_armor}"
        
    
    async def _get_instances(
        self,
        test_postgres_engine: AsyncEngine,
        input_ids: List[int],
    ) -> List[HeroDataTable]:
        
        async with AsyncSession(test_postgres_engine) as session:
            async with session.begin():
                stmt = select(HeroDataTable).where(HeroDataTable.id.in_(input_ids)) # type: ignore
                res = await session.execute(stmt)
                
                stored_heroes = res.scalars().all()
                session.expunge_all() # note to use expunge all to expunge all objects
                
        
        return stored_heroes # type: ignore
    
    
    def _assert_equal(self, actual_instance: HeroDataTable, expected_instance: HeroDataTable):
        
        for field in HeroDataTable.model_fields.keys():
            expected_value = getattr(expected_instance, field)
            actual_value = getattr(actual_instance, field)
            
            assert expected_value == actual_value, (
                f"values mismatch for field {field}"
                f"expected {expected_value}, got {actual_value}"
            )