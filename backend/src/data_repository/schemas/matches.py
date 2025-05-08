from typing import Optional
from sqlmodel import SQLModel, Field 
from sqlalchemy import BigInteger, Column, TIMESTAMP 
from datetime import datetime

class MatchTable(SQLModel, table=True):
    __tablename__ = "matches"
    # Primary Key
    match_id: int = Field(default=None, sa_column=Column('match_id', BigInteger, primary_key=True))
    
    # Columns for hero IDs:
    slot_0_hero_id: Optional[int] = Field(default=None) 
    slot_1_hero_id: Optional[int] = Field(default=None)
    slot_2_hero_id: Optional[int] = Field(default=None)
    slot_3_hero_id: Optional[int] = Field(default=None)
    slot_4_hero_id: Optional[int] = Field(default=None)
    slot_128_hero_id: Optional[int] = Field(default=None)
    slot_129_hero_id: Optional[int] = Field(default=None)
    slot_130_hero_id: Optional[int] = Field(default=None)
    slot_131_hero_id: Optional[int] = Field(default=None)
    slot_132_hero_id: Optional[int] = Field(default=None)
    
    # Columns for account IDs:
    slot_0_account_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True)) 
    slot_1_account_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True)) 
    slot_2_account_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True)) 
    slot_3_account_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True)) 
    slot_4_account_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True)) 
    slot_128_account_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True)) 
    slot_129_account_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True)) 
    slot_130_account_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True)) 
    slot_131_account_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True)) 
    slot_132_account_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True)) 
    
    radiant_name: Optional[str] = Field(default=None)
    radiant_team_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True)) 
    dire_name: Optional[str] = Field(default=None)
    dire_team_id: Optional[int] = Field(default=None, sa_column=Column(BigInteger, nullable=True)) 
    
    start_time: Optional[datetime] = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    ) 
    duration: Optional[float] = Field(default=None)

class MatchOutcomeTable(SQLModel, table=True):
    __tablename__ = 'match_outcomes'
    
    match_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True) 
    )
    
    radiant_win: Optional[bool] = Field(default=None) 
