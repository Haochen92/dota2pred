"""
Shared fixtures and base classes for features repository tests.
"""
import pytest
import pytest_asyncio
from dota_oracle.utils import get_logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel
from typing import TypeVar

from dota_oracle.data_repository.features_repository import FeaturesRepository

from ....factories.repository_factories import (
    PlayerHeroFeatureTableFactory,
    TeamFeaturesTableFactory,
    HeroFeaturesTableFactory,
    MatchTableFactory
)

from dota_oracle.models.features import PlayerHeroFeatureTable, TeamFeaturesTable, HeroFeaturesTable


T = TypeVar("T", bound=SQLModel)

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session')

# ========================
# FIXTURES
# ========================

@pytest_asyncio.fixture(scope="function")
async def features_repository_test_subject(db_session: AsyncSession) -> FeaturesRepository:
    """Create FeaturesRepository instance for testing."""
    return FeaturesRepository(session=db_session)


@pytest_asyncio.fixture(scope='function')
async def seed_prerequisite_match_ids_fk(db_session: AsyncSession):
    """Seeds foreign key dependency data (MatchTable) required for features."""
    logger.debug("Seeding prerequisite match IDs for current test transaction...")
    # Include all match_ids used across all tests
    match_ids_new = [1011, 1012]  
    match_ids_existing = [1001, 1002, 1003]
    match_ids_all = match_ids_new + match_ids_existing
    
    match_table_instances = [MatchTableFactory.build(match_id=test_match_id) for test_match_id in match_ids_all]
    
    db_session.add_all(match_table_instances)
    await db_session.commit()
    
    logger.debug("Prerequisite match data seeded for current test transaction.")

@pytest_asyncio.fixture(scope="function")
async def seed_features_data(db_session: AsyncSession, seed_prerequisite_match_ids_fk):
    """Seeds data for features repository tests"""
    
    logger.info("Seeding features data")
    
    # Create seed data as dictionaries keyed by match_id
    team_features_data = {
        1001: TeamFeaturesTableFactory.build(match_id=1001),
        1002: TeamFeaturesTableFactory.build(match_id=1002),
    }
    
    hero_features_data = {
        1003: HeroFeaturesTableFactory.build(match_id=1003)
    }
    
    player_hero_feature_data = {
        1001: PlayerHeroFeatureTableFactory.build(match_id=1001),
        1002: PlayerHeroFeatureTableFactory.build(match_id=1002),
        1003: PlayerHeroFeatureTableFactory.build(match_id=1003),
    }
    
    all_data = (
        list(team_features_data.values()) + 
        list(hero_features_data.values()) + 
        list(player_hero_feature_data.values())
    )
    
    db_session.add_all(all_data)
    await db_session.commit()
    
    logger.info("Seeding complete.")
    
    seeded_instance_dict = {
        TeamFeaturesTable.__name__ : team_features_data,
        PlayerHeroFeatureTable.__name__ : player_hero_feature_data,
        HeroFeaturesTable.__name__ : hero_features_data
    }
    
    yield seeded_instance_dict
    


