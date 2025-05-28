from typing import Optional
from sqlmodel import SQLModel, Field 
from sqlalchemy import BigInteger, Column, TIMESTAMP 
from datetime import datetime

class MatchTable(SQLModel, table=True):
    __tablename__ = "matches"  # type: ignore
    # Primary Key
    match_id: int = Field(default=None, sa_column=Column('match_id', BigInteger, primary_key=True))
    
    # League id
    leagueid: Optional[int] = None
    
    # Columns for hero IDs:
    slot_0_hero_id: str
    slot_1_hero_id: str 
    slot_2_hero_id: str 
    slot_3_hero_id: str 
    slot_4_hero_id: str 
    slot_128_hero_id: str 
    slot_129_hero_id: str 
    slot_130_hero_id: str 
    slot_131_hero_id: str 
    slot_132_hero_id: str 
    
    # Columns for account IDs:
    slot_0_account_id: int = Field(default=None, sa_column=Column(BigInteger, nullable=False)) 
    slot_1_account_id: int = Field(default=None, sa_column=Column(BigInteger, nullable=False)) 
    slot_2_account_id: int = Field(default=None, sa_column=Column(BigInteger, nullable=False)) 
    slot_3_account_id: int = Field(default=None, sa_column=Column(BigInteger, nullable=False)) 
    slot_4_account_id: int = Field(default=None, sa_column=Column(BigInteger, nullable=False)) 
    slot_128_account_id: int = Field(default=None, sa_column=Column(BigInteger, nullable=False)) 
    slot_129_account_id: int = Field(default=None, sa_column=Column(BigInteger, nullable=False)) 
    slot_130_account_id: int = Field(default=None, sa_column=Column(BigInteger, nullable=False)) 
    slot_131_account_id: int = Field(default=None, sa_column=Column(BigInteger, nullable=False)) 
    slot_132_account_id: int = Field(default=None, sa_column=Column(BigInteger, nullable=False)) 
    
    radiant_name: Optional[str] = Field(default=None)
    radiant_team_id: int = Field(default=None, sa_column=Column(BigInteger, nullable=False)) 
    dire_name: Optional[str] = Field(default=None)
    dire_team_id: int = Field(default=None, sa_column=Column(BigInteger, nullable=False)) 
    
    start_time: datetime = Field(
        default=None,
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    ) 
    duration: Optional[float] = Field(default=None)

class MatchOutcomeTable(SQLModel, table=True):
    __tablename__ = 'match_outcomes' # type: ignore
    
    match_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True) 
    )
    
    radiant_win: bool = Field(default=None) 
