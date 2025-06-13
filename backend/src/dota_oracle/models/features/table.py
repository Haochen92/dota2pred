from sqlmodel import Field, Relationship
from sqlalchemy import BigInteger, Column, JSON
from .schema import TeamFeatures, PlayerHeroFeature, HeroFeatures
from typing import List


class TeamFeaturesTable(TeamFeatures, table=True):
    """Database table for team-based features.
    
    Links to matches table with computed team features.
    
    Attributes:
        match_id: Primary/foreign key to matches (BigInteger)
        radiant_dire_matchup: Team matchup strength (float)
        radiant_win_rate: Radiant team win rate (float)
        dire_win_rate: Dire team win rate (float)
    
    Relationships:
        match: Related MatchTable instance
    """
    """
    Feature model for match data with match_id as both primary and foreign key.
    This links to the matches table while storing computed features.
    """
    __tablename__ = 'team_features' # type: ignore

    # Overrides
    match_id: int = Field(sa_type=BigInteger, primary_key=True, 
                          foreign_key="matches.match_id")

    # Relationships
    match: "MatchTable" = Relationship(back_populates="team_features")



class HeroFeaturesTable(HeroFeatures, table=True):
    """Database table for hero-based features.
    
    Attributes:
        match_id: Primary/foreign key to matches (BigInteger)
        hero_picks: List of hero picks stored as JSON (List[str])
    
    Relationships:
        match: Related MatchTable instance
    """
    __tablename__ = 'hero_features' # type: ignore
    
    # Overrides
    # Primary key
    match_id: int = Field(sa_type=BigInteger, primary_key=True, 
                          foreign_key="matches.match_id")
    
    hero_picks: List[str] = Field(sa_column=Column(JSON))
    
    # Relationship
    match: "MatchTable" = Relationship(back_populates="hero_features")

class PlayerHeroFeatureTable(PlayerHeroFeature, table=True):
    """Database table for player-hero combination features.
    
    Attributes:
        match_id: Primary/foreign key to matches (BigInteger)
        player_hero_*_win_rate: Win rates for all 10 player-hero combinations (float)
    
    Relationships:
        match: Related MatchTable instance
    """
    __tablename__ = 'player_hero_features' # type: ignore
    
    # Overrides
    # Primary key
    match_id: int = Field(sa_type=BigInteger, primary_key=True, 
                          foreign_key="matches.match_id") 

    # Relationship
    match: "MatchTable" = Relationship(back_populates="player_hero_features")
