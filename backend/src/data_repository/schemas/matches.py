from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column

class MatchTable(SQLModel, table=True):
    __tablename__ = "matches"
    # Primary Key
    match_id: int = Field(default=None,sa_column=Column('match_id', BigInteger, primary_key=True))
    
    # Columns for hero IDs:
    slot_0_hero_id: Optional[float] = Field(default=None)
    slot_1_hero_id: Optional[float] = Field(default=None)
    slot_2_hero_id: Optional[float] = Field(default=None)
    slot_3_hero_id: Optional[float] = Field(default=None)
    slot_4_hero_id: Optional[float] = Field(default=None)
    slot_128_hero_id: Optional[float] = Field(default=None)
    slot_129_hero_id: Optional[float] = Field(default=None)
    slot_130_hero_id: Optional[float] = Field(default=None)
    slot_131_hero_id: Optional[float] = Field(default=None)
    slot_132_hero_id: Optional[float] = Field(default=None)
    
    # Columns for account IDs:
    slot_0_account_id: Optional[float] = Field(default=None)
    slot_1_account_id: Optional[float] = Field(default=None)
    slot_2_account_id: Optional[float] = Field(default=None)
    slot_3_account_id: Optional[float] = Field(default=None)
    slot_4_account_id: Optional[float] = Field(default=None)
    slot_128_account_id: Optional[float] = Field(default=None)
    slot_129_account_id: Optional[float] = Field(default=None)
    slot_130_account_id: Optional[float] = Field(default=None)
    slot_131_account_id: Optional[float] = Field(default=None)
    slot_132_account_id: Optional[float] = Field(default=None)
    
    radiant_name: Optional[str] = Field(default=None)
    radiant_team_id: Optional[float] = Field(default=None)
    dire_name: Optional[str] = Field(default=None)
    dire_team_id: Optional[float] = Field(default=None)
    start_time: Optional[float] = Field(default=None)
    duration: Optional[float] = Field(default=None)

class MatchOutcomeTable(SQLModel, table=True):
    __tablename__ = 'match_outcomes'
    # primary key
    match_id: int = Field(sa_type=BigInteger, primary_key=True, 
                          foreign_key="matches.match_id")
    
    radiant_win: bool = Field(default=None, nullable=True)

