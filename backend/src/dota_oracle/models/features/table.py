from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import BigInteger, Column, JSON
from typing import List


class TeamFeaturesTable(SQLModel, table=True):
    """
    Feature model for match data with match_id as both primary and foreign key.
    This links to the matches table while storing computed features.
    """
    __tablename__ = 'team_features' # type: ignore

    match_id: int = Field(sa_type=BigInteger, primary_key=True, 
                          foreign_key="matches.match_id")

    
    # Feature columns
    radiant_dire_matchup: float
    radiant_win_rate: float
    dire_win_rate: float
    
    # Relationships
    match: "MatchTable" = Relationship(back_populates="team_features")



class HeroFeaturesTable(SQLModel, table=True):
    __tablename__ = 'hero_features' # type: ignore
    
    # Primary key
    match_id: int = Field(sa_type=BigInteger, primary_key=True, 
                          foreign_key="matches.match_id")
    
    # Feature columns
    hero_picks: List[str] = Field(sa_column=Column(JSON))

    # Relationship
    match: "MatchTable" = Relationship(back_populates="hero_features")

class PlayerHeroFeatureTable(SQLModel, table=True):
    __tablename__ = 'player_hero_features' # type: ignore
    # Primary key
    match_id: int = Field(sa_type=BigInteger, primary_key=True, 
                          foreign_key="matches.match_id")
    
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

    # Relationship
    match: "MatchTable" = Relationship(back_populates="player_hero_features")
