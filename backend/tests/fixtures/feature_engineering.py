"""
Feature engineering component fixtures for tests.
"""
import pytest

# Core ML Pipeline Imports
from dota_oracle.feature_engineering import (
    PlayerHeroFeaturesCreator, 
    TeamFeatureCreator, 
    HeroesFeatureCreator
)


# ================================
# COMPONENT FIXTURES
# ================================

@pytest.fixture
def player_hero_features_creator() -> PlayerHeroFeaturesCreator:
    return PlayerHeroFeaturesCreator(max_history_length=20)


@pytest.fixture
def team_feature_creator() -> TeamFeatureCreator:
    return TeamFeatureCreator()


@pytest.fixture
def heroes_feature_creator() -> HeroesFeatureCreator:
    return HeroesFeatureCreator()