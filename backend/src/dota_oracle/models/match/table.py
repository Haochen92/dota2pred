from typing import Optional, List
from sqlmodel import Field, Relationship
from sqlalchemy import BigInteger, Column, TIMESTAMP, ForeignKey 
from datetime import datetime
from .base import Match, MatchOutcome

class MatchTable(Match, table=True):
    __tablename__ = "matches"  # type: ignore
    # Primary Key
    match_id: int = Field(sa_column=Column('match_id', BigInteger, primary_key=True))
    
    # Columns for account IDs:
    slot_0_account_id: int = Field(sa_column=Column(BigInteger, nullable=False)) 
    slot_1_account_id: int = Field(sa_column=Column(BigInteger, nullable=False)) 
    slot_2_account_id: int = Field(sa_column=Column(BigInteger, nullable=False)) 
    slot_3_account_id: int = Field(sa_column=Column(BigInteger, nullable=False)) 
    slot_4_account_id: int = Field(sa_column=Column(BigInteger, nullable=False)) 
    slot_128_account_id: int = Field(sa_column=Column(BigInteger, nullable=False)) 
    slot_129_account_id: int = Field(sa_column=Column(BigInteger, nullable=False)) 
    slot_130_account_id: int = Field(sa_column=Column(BigInteger, nullable=False)) 
    slot_131_account_id: int = Field(sa_column=Column(BigInteger, nullable=False)) 
    slot_132_account_id: int = Field(sa_column=Column(BigInteger, nullable=False)) 
    
    radiant_team_id: int = Field(sa_column=Column(BigInteger, nullable=False)) 
    dire_team_id: int = Field(sa_column=Column(BigInteger, nullable=False)) 
    
    start_time: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    
    # Relationships
    outcome: Optional["MatchOutcomeTable"] = Relationship(
        back_populates="match",
        sa_relationship_kwargs={'uselist':False, 'cascade': "all, delete-orphan"}
    )
    predictions: List["MatchPredictionTable"] = Relationship(
        back_populates="match",
        sa_relationship_kwargs={'cascade': "all, delete-orphan"}
    )
    
    team_features: Optional["TeamFeaturesTable"] = Relationship(
        back_populates="match",
        sa_relationship_kwargs={'uselist':False, 'cascade': "all, delete-orphan"}
    )
    player_hero_features: Optional["PlayerHeroFeatureTable"] = Relationship(
        back_populates="match",
        sa_relationship_kwargs={'uselist':False, 'cascade': "all, delete-orphan"}
    )
    hero_features: Optional["HeroFeaturesTable"] = Relationship(
        back_populates="match",
        sa_relationship_kwargs={'uselist':False, 'cascade': "all, delete-orphan"}
    )

class MatchOutcomeTable(MatchOutcome, table=True):
    __tablename__ = 'match_outcomes' # type: ignore
    
    match_id: int = Field(
        sa_column=Column(BigInteger, ForeignKey("matches.match_id"), primary_key=True) 
    )
    
    # Relationship
    match: "MatchTable" = Relationship( back_populates="outcome")
    
