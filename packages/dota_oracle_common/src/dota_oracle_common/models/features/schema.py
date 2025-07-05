from typing import List
from sqlmodel import SQLModel


class TeamFeatures(SQLModel):
    """Base Model for team-based features.

    Links to matches table with computed team features.

    Attributes:
        match_id: Primary/foreign key to matches (BigInteger)
        radiant_dire_matchup: Team matchup strength (float)
        radiant_win_rate: Radiant team win rate (float)
        dire_win_rate: Dire team win rate (float)

    """

    # Feature columns
    radiant_dire_matchup: float
    radiant_win_rate: float
    dire_win_rate: float


class HeroFeatures(SQLModel):
    """Base Model for hero-based features.

    Attributes:
        match_id: Primary/foreign key to matches (BigInteger)
        hero_picks: List of hero picks stored as JSON (List[str])

    """

    # Feature columns
    hero_picks: List[int]


class PlayerHeroFeature(SQLModel):
    """Base Model for player-hero combination features.

    Attributes:
        match_id: Primary/foreign key to matches (BigInteger)
        player_hero_*_win_rate: Win rates for all 10 player-hero combinations (float)

    """

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
