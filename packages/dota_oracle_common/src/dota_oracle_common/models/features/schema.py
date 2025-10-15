from typing import List

from pydantic import BaseModel, Field
from sqlmodel import SQLModel


class TeamFeatures(SQLModel):
    """Base Model for team-based features.

    Links to matches table with computed team features.

    Attributes:
        match_id: Primary/foreign key to matches (int)
        radiant_dire_matchup: Team matchup strength (float)
        radiant_win_rate: Radiant team win rate (float)
        dire_win_rate: Dire team win rate (float)

    """

    # Match identifier
    match_id: int

    # Feature columns
    radiant_dire_matchup: float
    radiant_win_rate: float
    dire_win_rate: float


class HeroFeatures(SQLModel):
    """Base Model for hero-based features.

    Attributes:
        match_id: Primary/foreign key to matches (int)
        hero_picks: List of hero picks stored as JSON (List[int])

    """

    # Match identifier
    match_id: int

    # Feature columns
    hero_picks: List[int]


class PlayerHeroFeature(SQLModel):
    """Base Model for player-hero combination features.

    Attributes:
        match_id: Primary/foreign key to matches (int)
        player_hero_*_win_rate: Win rates for all 10 player-hero combinations (float)

    """

    # Match identifier
    match_id: int

    # Features
    player_hero_0_win_rate: float
    player_hero_1_win_rate: float
    player_hero_2_win_rate: float
    player_hero_3_win_rate: float
    player_hero_4_win_rate: float
    player_hero_128_win_rate: float
    player_hero_129_win_rate: float
    player_hero_130_win_rate: float
    player_hero_131_win_rate: float
    player_hero_132_win_rate: float


class AllFeaturesDTO(TeamFeatures, HeroFeatures, PlayerHeroFeature):
    """
    A DTO that aggregates all features for a match with a GUARANTEED field order
    suitable for creating a feature vector for a machine learning model.
    """

    # By re-declaring the fields here, we enforce a specific order.
    # The types and other metadata are inherited from the parent classes.

    # 0. Match identifier
    match_id: int

    # 1. Team Features
    radiant_win_rate: float
    dire_win_rate: float
    radiant_dire_matchup: float

    # 2. Player-Hero Features (in their specific order)
    player_hero_0_win_rate: float
    player_hero_1_win_rate: float
    player_hero_2_win_rate: float
    player_hero_3_win_rate: float
    player_hero_4_win_rate: float
    player_hero_128_win_rate: float
    player_hero_129_win_rate: float
    player_hero_130_win_rate: float
    player_hero_131_win_rate: float
    player_hero_132_win_rate: float

    # 3. Hero Features (Categorical/Non-numeric features often go last)
    hero_picks: List[int]


class TeamFeaturesHyperparams(BaseModel):
    prior_mean: float = Field(..., gt=0.0, lt=1.0, description="Prior mean for team decay Bayesian smoothing")
    prior_count: float = Field(..., gt=0.0, description="Total pseudo-count associated with the team decay prior")
    half_life_days: int = Field(..., gt=0, description="Half-life window for team decay feature smoothing")


class HeroFeaturesHyperparams(BaseModel):
    prior_mean: float = Field(..., gt=0.0, lt=1.0, description="Prior mean for hero win rate decay smoothing")
    prior_count: float = Field(..., gt=0.0, description="Total pseudo-count associated with the hero decay prior")
    half_life_days: int = Field(..., gt=0, description="Half-life window for hero win rate decay feature")


class PlayerHeroFeaturesHyperparams(BaseModel):
    player_prior_count: float = Field(..., gt=0.0, description="Credibility (pseudo-count) used for player-hero dynamic prior blending")
    player_half_life_days: int = Field(..., gt=0, description="Half-life window for player performance decay")
    hero_prior_mean: float = Field(..., gt=0.0, lt=1.0, description="Prior mean for hero decay within player-hero dynamic prior")
    hero_prior_count: float = Field(..., gt=0.0, description="Total pseudo-count for hero decay within the player-hero dynamic prior")
    hero_half_life_days: int = Field(..., gt=0, description="Half-life window for hero decay within player-hero dynamic prior")


class FeatureHyperparams(BaseModel):
    team_features: TeamFeaturesHyperparams = Field(..., description="Hyperparameters for team decay feature generation")
    hero_features: HeroFeaturesHyperparams = Field(..., description="Hyperparameters for hero win rate feature generation")
    player_hero_features: PlayerHeroFeaturesHyperparams = Field(..., description="Hyperparameters for player-hero dynamic prior feature generation")
