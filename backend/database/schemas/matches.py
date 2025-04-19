from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column

class ProMatch(SQLModel, table=True):
    __tablename__ = "pro_matches"
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
    radiant_win: Optional[bool] = Field(default=None)

class ProMatchID(SQLModel, table=True):
    # Transient table, serving as checkpoint for fetching match_details using pro matches match_id
    __tablename__ = "pro_matches_id"
    
    match_id: int = Field(sa_column=Column(BigInteger, primary_key=True, autoincrement=False))
