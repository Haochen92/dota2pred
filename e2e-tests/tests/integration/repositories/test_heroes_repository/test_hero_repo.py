import pytest
from ..base_test_repository import BaseTestRepository

from dota_oracle_common.repositories.heroes_repository import HeroesRepository
from dota_oracle_common.models.heroes import HeroDataTable
from dota_oracle_common.utils import get_logger 

from typing import Dict


logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope="session")

class TestStoreHeroData:
    """Test class for hero data storage operations."""
    
    async def test_store_new_data(
        self,
        hero_repository_test_subject: HeroesRepository,
        test_repository: BaseTestRepository,
        hero_data_table_factory,
    ):
        """Test storing new hero data successfully inserts records."""
        # ARRANGE
        input_data = {
            'anti-mage': hero_data_table_factory.build(id=10, localized_name='anti-mage'),
            'lina': hero_data_table_factory.build(id=11, localized_name='lina')
        }
        
        # ACT
        await hero_repository_test_subject.store_hero_data(input_data) 
        
        # Use base repository method to get data
        stored_heroes = await test_repository._get_data(
            model_class=HeroDataTable,
            id_filters=[10, 11]
        )
        
        # ASSERT
        test_repository._assert_count_equal(
            actual_count=len(stored_heroes), 
            expected_count=len(input_data),
            test_scenario="store_new_data - record count"
        )
        
        for hero_data in stored_heroes:
            hero_name = hero_data.localized_name
            
            assert hero_name in set(input_data.keys()), \
                f"extracted hero data has different localised name: {hero_name}"
            
            input_instance = input_data[hero_name]
            
            test_repository._assert_equal(
                expected_instance=input_instance,
                actual_instance=hero_data,
                test_scenario=f"store_new_data - {hero_name} field comparison"
            )
            
    async def test_update_data_for_existing(
        self,
        hero_repository_test_subject: HeroesRepository,
        test_repository: BaseTestRepository,
        hero_data_table_factory,
    ):
        """Test updating existing hero data modifies records correctly."""
        # ARRANGE
        initial_data = {'Sven': hero_data_table_factory.build(id=13, localized_name='Sven', base_armor=5.3)}
        
        # ACT - Initial insert
        await hero_repository_test_subject.store_hero_data(initial_data)
        
        # Fetch stored data using base repository method
        stored_hero_data = await test_repository._get_data(
            model_class=HeroDataTable,
            id_filters=[13]
        )
        
        # ASSERT - Validate initial insert
        test_repository._assert_count_equal(
            actual_count=len(stored_hero_data), 
            expected_count=len(initial_data),
            test_scenario="update_existing_data - initial insert count"
        )
        
        for hero_data in stored_hero_data:
            hero_name = hero_data.localized_name
            
            assert hero_name in set(initial_data.keys()), \
                f"extracted hero data has different localised name: {hero_name}"
            
            input_instance = initial_data[hero_name]
            
            test_repository._assert_equal(
                expected_instance=input_instance,
                actual_instance=hero_data,
                test_scenario=f"update_existing_data - initial {hero_name} comparison"
            )
        
        # ACT - Update with modified data
        reinsert_data = {'Sven': hero_data_table_factory.build(id=13, localized_name='Sven', base_armor=10.6)}
        await hero_repository_test_subject.store_hero_data(reinsert_data)
        
        # Fetch updated data
        updated_hero_data = await test_repository._get_data(
            model_class=HeroDataTable,
            id_filters=[13]
        )
        
        # ASSERT - Validate update
        test_repository._assert_count_equal(
            actual_count=len(updated_hero_data), 
            expected_count=1,
            test_scenario="update_existing_data - updated record count"
        )
        
        data_instance = updated_hero_data[0]
        expected_instance = reinsert_data['Sven']
        
        test_repository._assert_equal(
            expected_instance=expected_instance,
            actual_instance=data_instance,
            test_scenario="update_existing_data - updated Sven comparison"
        )
        
        # Specific assertion for the updated field
        assert data_instance.base_armor == 10.6, \
            f"expected updated base_armor to be 10.6, got {data_instance.base_armor}"


class TestGetHeroIdMap:
    """Test class for hero ID mapping operations."""
    
    async def test_get_hero_map(self, 
        hero_repository_test_subject: HeroesRepository,
        test_repository: BaseTestRepository,
        seed_hero_data: Dict[int, str],
    ):
        """Test getting hero ID map returns correct mapping."""
        # ACT
        actual_hero_map = await hero_repository_test_subject.get_hero_id_map()
        
        # ASSERT
        test_repository._assert_count_equal(
            actual_count=len(actual_hero_map), 
            expected_count=len(seed_hero_data),
            test_scenario="get_hero_map - map size"
        )
        
        for key, expected_value in seed_hero_data.items():
            actual_value = actual_hero_map.get(key)
            
            assert expected_value == actual_value, (
                f"get_hero_map test: Values mismatch for key: {key}, "
                f"expected {expected_value}, got {actual_value}"
            )