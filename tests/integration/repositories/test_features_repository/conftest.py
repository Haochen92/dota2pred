"""
Shared fixtures and base classes for features repository tests.
"""
import pytest
import pytest_asyncio
from dota_oracle_common.utils import get_logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel
from typing import TypeVar

from dota_oracle_common.repositories.features_repository import FeaturesRepository

from dota_oracle_common.models.features import PlayerHeroFeatureTable, TeamFeaturesTable, HeroFeaturesTable


T = TypeVar("T", bound=SQLModel)

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session')

# ========================
# FIXTURES
# ========================


@pytest_asyncio.fixture(scope='function')
async def seed_prerequisite_match_ids_fk(db_session: AsyncSession, match_table_factory):
    """Seeds foreign key dependency data (MatchTable) required for features."""
    logger.debug("Seeding prerequisite match IDs for current test transaction...")
    # Include all match_ids used across all tests
    match_ids_new = [1011, 1012]  
    match_ids_existing = [1001, 1002, 1003]
    match_ids_all = match_ids_new + match_ids_existing
    
    match_table_instances = [match_table_factory.build(match_id=test_match_id) for test_match_id in match_ids_all]
    
    db_session.add_all(match_table_instances)
    await db_session.commit()
    
    logger.debug("Prerequisite match data seeded for current test transaction.")

@pytest_asyncio.fixture(scope="function")
async def seed_features_data(db_session: AsyncSession, seed_prerequisite_match_ids_fk, team_features_table_factory, hero_features_table_factory, player_hero_feature_table_factory):
    """Seeds data for features repository tests"""
    
    logger.info("Seeding features data")
    
    # Create seed data as dictionaries keyed by match_id
    team_features_data = {
        1001: team_features_table_factory.build(match_id=1001),
        1002: team_features_table_factory.build(match_id=1002),
    }
    
    hero_features_data = {
        1003: hero_features_table_factory.build(match_id=1003)
    }
    
    player_hero_feature_data = {
        1001: player_hero_feature_table_factory.build(match_id=1001),
        1002: player_hero_feature_table_factory.build(match_id=1002),
        1003: player_hero_feature_table_factory.build(match_id=1003),
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
    


