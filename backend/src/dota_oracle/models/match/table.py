from typing import Optional
from sqlmodel import Field, Relationship
from sqlalchemy import BigInteger, Column, TIMESTAMP 
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
    
    # Relationship
    outcome: Optional["MatchOutcomeTable"] = Relationship(
        back_populates="matches",
        sa_relationship_kwargs={}
    )

class MatchOutcomeTable(MatchOutcome, table=True):
    __tablename__ = 'match_outcomes' # type: ignore
    
    match_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True, foreign_key="matches.match_id") 
    )
    
