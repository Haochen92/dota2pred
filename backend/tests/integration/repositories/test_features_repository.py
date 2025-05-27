import pytest
import pytest_asyncio
from dota_oracle.utils import get_logger
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import delete
from sqlmodel import select, SQLModel
from typing import Dict, List, Any, TypeVar, Type
from polyfactory.factories.pydantic_factory import ModelFactory

from dota_oracle.data_repository.features_repository import FeaturesRepository

from ...factories.repository_factories import (
    PlayerHeroFeatureTableFactory,
    TeamFeaturesTableFactory,
    HeroFeaturesTableFactory,
    MatchTableFactory
)

from dota_oracle.data_repository.schemas import (
    PlayerHeroFeatureTable,
    TeamFeaturesTable,
    HeroFeaturesTable,
    MatchTable
)

T = TypeVar("T", bound=SQLModel)

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session')

@pytest_asyncio.fixture(scope="function")
async def features_repository_test_subject(test_postgres_engine: AsyncEngine) -> FeaturesRepository:
    return FeaturesRepository(engine=test_postgres_engine)


'''
-- TEST STORE FEATURES ---
'''
TEST_STORE_FEATURES_ARGS = [
    "test_id",
    "input_factory",
    "input_table_class",
    "expected_fields"
]

TEST_STORE_FEATURES_SCENARIOS = [
    (
        'hero_features_new',
        HeroFeaturesTableFactory,
        HeroFeaturesTable,
        {
            'match_id': 1011,
            'hero_picks': ["pangolier","puck","windranger"]
        }
    ),
    (
        'hero_features_existing_match_id',
        HeroFeaturesTableFactory,
        HeroFeaturesTable,
        {
            'match_id': 1003,
            'hero_picks': ["drow_ranger","anti_mage","spectre"]
        }
    ),
    (
        'team_features_happy_new',
        TeamFeaturesTableFactory,
        TeamFeaturesTable,
        {
            'match_id': 1011, 
            'radiant_dire_matchup': 0.7,
            'radiant_win_rate': 0.4,
            'dire_win_rate': 0.5
        }
    ),
    (
        'player_hero_features_happy_new',
        PlayerHeroFeatureTableFactory,
        PlayerHeroFeatureTable,
        {
            'match_id': 1011,
            'player_hero_0_win_rate': 0.1,
            'player_hero_1_win_rate': 0.1,
            'player_hero_2_win_rate': 0.3,
            'player_hero_3_win_rate': 0.3,
            'player_hero_4_win_rate': 0.5,
            'player_hero_128_win_rate': 0.4,
            'player_hero_129_win_rate': 0.1,
            'player_hero_130_win_rate': 0.83,
            'player_hero_131_win_rate': 0.99,
            'player_hero_132_win_rate': 0.01,
        }
    ),
]

@pytest.mark.parametrize(TEST_STORE_FEATURES_ARGS, TEST_STORE_FEATURES_SCENARIOS)
@pytest.mark.usefixtures("seed_features_data")
async def test_store_features(
    features_repository_test_subject: FeaturesRepository,
    test_postgres_engine: AsyncEngine,
    test_id: str,
    input_factory: ModelFactory,  
    input_table_class: Type[T],
    expected_fields: Dict[str, Any]
):
    """Test storing features to database"""
    
    # Act 
    input_match_id = expected_fields.get('match_id')
    assert input_match_id is not None, f"{test_id}: invalid_test input, missing match_id"
    
    input_instance = input_factory.build(**expected_fields)
    
    await features_repository_test_subject.store_features([input_instance], input_table_class)
    
    # Assert - verify the data was stored correctly
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            stmt = select(input_table_class).where(input_table_class.match_id == input_match_id) # type: ignore
            
            result = await session.execute(stmt)
            records = result.scalars().all()
            
            assert len(records) == 1, f"{test_id}: expected 1 result, got {len(records)}"
            
            actual_instance = records[0]
            
            for field_name, expected_value in expected_fields.items():
                actual_value = getattr(actual_instance, field_name)
                assert actual_value == expected_value, (
                    f"{test_id}: Field '{field_name}' - expected {expected_value}, got {actual_value}"
                )


@pytest.mark.usefixtures("seed_features_data")
async def test_store_features_empty_list(
    features_repository_test_subject: FeaturesRepository
):
    """Test that storing empty list handles gracefully"""
    # Should not raise an exception and should return without doing anything
    await features_repository_test_subject.store_features([], TeamFeaturesTable)


"""
-- TEST GET FEATURE BY ID ---
"""
GET_FEATURE_BY_ID_ARGS = [
    "test_id",
    "test_match_id",
    "test_feature_table_class",
    "expected_fields"
]

GET_FEATURE_BY_ID_SCENARIOS = [
    (
        "get_team_features_happy",
        1001,
        TeamFeaturesTable,
        {
            "match_id":1001,
            "radiant_dire_matchup": 0.65,
            "radiant_win_rate": 0.4,
            "dire_win_rate": 0.8
        }
    ),
    (
        "get_hero_feature_happy",
        1003,
        HeroFeaturesTable,
        {
            "match_id": 1003,
            "hero_picks": ['mirana','windrunner','crystal_maiden']
        }
    ),
    (
        "get_player_hero_feature_happy",
        1003,
        PlayerHeroFeatureTable,
        {
            "match_id": 1003,
            "player_hero_0_win_rate": 0.1,
            "player_hero_1_win_rate": 0.2,
            "player_hero_2_win_rate": 0.3,
            "player_hero_3_win_rate": 0.4,
            "player_hero_4_win_rate": 0.5,
            "player_hero_128_win_rate": 0.6,
            "player_hero_129_win_rate": 0.7,
            "player_hero_130_win_rate": 0.8,
            "player_hero_131_win_rate": 0.9,
            "player_hero_132_win_rate": 1.0
        }
    )
]

@pytest.mark.usefixtures("seed_features_data")
@pytest.mark.parametrize(GET_FEATURE_BY_ID_ARGS, GET_FEATURE_BY_ID_SCENARIOS)
async def test_get_feature_by_id(
    features_repository_test_subject: FeaturesRepository,
    test_id: str,
    test_match_id: int,
    test_feature_table_class: Type[T],
    expected_fields: Dict[str, Any]
):
    actual_instance = await features_repository_test_subject.get_feature_by_id(test_match_id, test_feature_table_class)

    for field_name, expected_value in expected_fields.items():
        actual_value = getattr(actual_instance, field_name)
        assert actual_value == expected_value, (
            f"{test_id}: Field '{field_name}' - expected {expected_value}, got {actual_value}"
        )



@pytest.mark.usefixtures("seed_features_data")
@pytest.mark.parametrize(
    "test_id, test_match_id, test_feature_table_class, expected_error_message",
    [
        ("missing_match_id", None, HeroFeaturesTable, "missing match_id"),
        ("midding_table_class", 1003, None, "missing feature_table_class"),
        ("invalid_class_type", 1003, dict, "feature_table_class must be a subclass of SQLModel")
    ]
)
async def test_get_feature_invalid_inputs_raise_errors(
    features_repository_test_subject: FeaturesRepository,
    test_id: str,
    test_match_id: int,
    test_feature_table_class: Type[T],
    expected_error_message: str
):
    with pytest.raises(ValueError, match=expected_error_message):
        logger.info(f"test_id: {test_id}")
        await features_repository_test_subject.get_feature_by_id(test_match_id, test_feature_table_class)


"""
--- Test Get all features ---
"""
@pytest.mark.usefixtures("seed_features_data")
async def test_get_all_features_from_table(
    features_repository_test_subject: FeaturesRepository,
):
    actual_instances = await features_repository_test_subject.get_all_features_from_table(TeamFeaturesTable)
    expected_instances_count = 2
    actual_instances_count = len(actual_instances)
    assert expected_instances_count == actual_instances_count, (
        f"Expected {expected_instances_count} results, got {actual_instances_count}"
    )


"""
-- Fixtures --
"""

@pytest_asyncio.fixture(scope="function")
async def seed_features_data(test_postgres_engine: AsyncEngine):
    """Seeds data for features repository tests"""
    
    logger.info("Seeding features data")
    
    # Create seed data that doesn't conflict with test scenarios
    team_features_data = [
        TeamFeaturesTableFactory.build(match_id=1001, radiant_dire_matchup=0.65, radiant_win_rate=0.4, dire_win_rate=0.8),
        TeamFeaturesTableFactory.build(match_id=1002, radiant_dire_matchup=0.53, radiant_win_rate=0.6, dire_win_rate=0.4),
    ]
    
    # Note: Using match_id=1003 to test upsert behavior in one of the test scenarios
    hero_features_data = [
        HeroFeaturesTableFactory.build(match_id=1003, hero_picks=['mirana','windrunner','crystal_maiden'])
    ]
    
    player_hero_feature_data = [
        PlayerHeroFeatureTableFactory.build(
            match_id=1003,
            player_hero_0_win_rate=0.1,
            player_hero_1_win_rate=0.2,
            player_hero_2_win_rate=0.3,
            player_hero_3_win_rate=0.4,
            player_hero_4_win_rate=0.5,
            player_hero_128_win_rate=0.6,
            player_hero_129_win_rate=0.7,
            player_hero_130_win_rate=0.8,
            player_hero_131_win_rate=0.9,
            player_hero_132_win_rate=1.0,
        )
    ]
        
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            all_data = team_features_data + hero_features_data + player_hero_feature_data
            for instance in all_data:
                session.add(instance)
            await session.commit()
            
    logger.info("Seeding complete.")

    yield
    
    # Cleanup
    logger.info("Cleaning up seeded features data...")
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(PlayerHeroFeatureTable))
            await session.execute(delete(TeamFeaturesTable))
            await session.execute(delete(HeroFeaturesTable))
            await session.commit()
        
    logger.info("Cleanup complete")
    

@pytest_asyncio.fixture(scope='module',autouse=True)
async def seed_prerequisite_match_ids_fk(test_postgres_engine:AsyncEngine):
    """_summary_

    Args:
        test_postgres_engine (AsyncEngine): 
        Seeds foreign key tables 
    """
    match_ids_new = [1011]
    match_ids_existing = [1001, 1002, 1003]
    match_ids_all = match_ids_new + match_ids_existing
    
    match_table_instances = [MatchTableFactory.build(match_id=test_match_id) for test_match_id in match_ids_all]
        
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            for instance in match_table_instances:
                session.add(instance)
            await session.commit()
            
        logger.info("Seeding complete.")

    yield
    
    # Cleanup
    logger.info("Cleaning up seeded features data...")
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(MatchTable))
            await session.commit()
        
    logger.info("Cleanup complete")
    
    
