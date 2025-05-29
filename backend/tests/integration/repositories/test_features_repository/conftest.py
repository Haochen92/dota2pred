"""
Shared fixtures and base classes for features repository tests.
"""
import pytest
import pytest_asyncio
from dota_oracle.utils import get_logger
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import delete
from sqlmodel import select, SQLModel
from typing import Dict, List, Any, TypeVar, Type, Set

from dota_oracle.data_repository.features_repository import FeaturesRepository

from ....factories.repository_factories import (
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


class BaseFeaturesRepositoryTest:
    """Base class with common assertion helpers and database operations for features repository tests."""
    
    # Database Operation Helpers
    async def _get_feature_by_id(self, engine: AsyncEngine, match_id: int, feature_class: Type[T]) -> T:
        """Retrieve a feature instance by match_id and table class."""
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(feature_class).where(feature_class.match_id == match_id)  # type: ignore
                result = await session.execute(stmt)
                instance = result.scalars().one()
                session.expunge(instance)
                return instance
    
    async def _get_all_features_from_table(self, engine: AsyncEngine, feature_class: Type[T]) -> List[T]:
        """Retrieve all features from a table."""
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(feature_class)
                result = await session.execute(stmt)
                instances = result.scalars().all()
                session.expunge_all()
                return instances
    
    async def _count_features_in_table(self, engine: AsyncEngine, feature_class: Type[T], match_ids: Set[int] = None) -> int:
        """Count features in a table, optionally filtered by match_ids."""
        async with AsyncSession(engine) as session:
            async with session.begin():
                if match_ids:
                    stmt = select(feature_class).where(feature_class.match_id.in_(match_ids))  # type: ignore
                else:
                    stmt = select(feature_class)
                result = await session.execute(stmt)
                return len(result.scalars().all())
    
    async def _feature_exists(self, engine: AsyncEngine, match_id: int, feature_class: Type[T]) -> bool:
        """Check if a feature exists for given match_id."""
        try:
            await self._get_feature_by_id(engine, match_id, feature_class)
            return True
        except Exception:
            return False
    
    # Assertion Helpers
    def _assert_feature_equals(self, expected: T, actual: T, feature_name: str = "", context: str = ""):
        """Compare feature instances field by field."""
        excluded_fields = {'_sa_instance_state'}
        
        # Get model fields - handle both SQLModel and regular models
        if hasattr(expected, 'model_fields'):
            fields = expected.model_fields.keys()
        elif hasattr(expected.__class__, '__table__'):
            fields = [col.name for col in expected.__class__.__table__.columns]
        else:
            # Fallback to dir() filtering
            fields = [attr for attr in dir(expected) if not attr.startswith('_') and not callable(getattr(expected, attr))]
        
        for field in fields:
            if field in excluded_fields:
                continue
                
            expected_value = getattr(expected, field)
            actual_value = getattr(actual, field)
            assert expected_value == actual_value, (
                f"{context} - {feature_name} field '{field}' mismatch: "
                f"expected {expected_value}, got {actual_value}"
            )
    
    def _assert_feature_fields_match(self, instance: T, expected_fields: Dict[str, Any], context: str = ""):
        """Assert that feature instance has expected field values."""
        for field_name, expected_value in expected_fields.items():
            actual_value = getattr(instance, field_name)
            assert actual_value == expected_value, (
                f"{context} - Field '{field_name}' mismatch: "
                f"expected {expected_value}, got {actual_value}"
            )
    
    def _assert_feature_count_equals(self, expected_count: int, actual_features: List[Any], context: str = ""):
        """Assert that the number of features matches expected count."""
        actual_count = len(actual_features)
        assert actual_count == expected_count, (
            f"{context} - Count mismatch: expected {expected_count}, got {actual_count}"
        )


# ========================
# FIXTURES
# ========================

@pytest_asyncio.fixture(scope="function")
async def features_repository_test_subject(test_postgres_engine: AsyncEngine) -> FeaturesRepository:
    """Create FeaturesRepository instance for testing."""
    return FeaturesRepository(engine=test_postgres_engine)


@pytest_asyncio.fixture(scope='session', autouse=True)
async def seed_prerequisite_match_ids_fk(test_postgres_engine: AsyncEngine):
    """Seeds foreign key dependency data (MatchTable) required for features."""
    # Include all match_ids used across all tests
    match_ids_new = [1011, 1012]  
    match_ids_existing = [1001, 1002, 1003]
    match_ids_all = match_ids_new + match_ids_existing
    
    match_table_instances = [MatchTableFactory.build(match_id=test_match_id) for test_match_id in match_ids_all]
        
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            for instance in match_table_instances:
                session.add(instance)
            
        logger.info("FK seeding complete.")

    yield
    
    # Cleanup
    logger.info("Cleaning up FK data...")
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            # Clean up children dependencies
            await session.execute(delete(PlayerHeroFeatureTable))
            await session.execute(delete(TeamFeaturesTable)) 
            await session.execute(delete(HeroFeaturesTable))
            
            # Clean up fk seeding
            await session.execute(delete(MatchTable))
        
            logger.info("FK cleanup complete")

@pytest_asyncio.fixture(scope="function", autouse=True)
async def clear_features_database(test_postgres_engine: AsyncEngine):
    """Clean up features tables between tests automatically."""
    await _clear_database(test_postgres_engine)
    logger.info(f"cleared database for set up...")
    
    yield
    
    await _clear_database(test_postgres_engine)
    logger.info(f"cleared database after test")
    
async def _clear_database(test_postgres_engine):
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            # Clean up children dependencies
            await session.execute(delete(PlayerHeroFeatureTable))
            await session.execute(delete(TeamFeaturesTable)) 
            await session.execute(delete(HeroFeaturesTable))
            

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
            
    logger.info("Seeding complete.")


