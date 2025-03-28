from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column, Float, Boolean, Text, UniqueConstraint

class ProMatch(SQLModel, table=True):
    __tablename__ = "pro_matches"
    
    # Columns for hero IDs:
    c0_hero_id: Optional[float] = Field(default=None, sa_column=Column("0_hero_id", Float))
    c1_hero_id: Optional[float] = Field(default=None, sa_column=Column("1_hero_id", Float))
    c2_hero_id: Optional[float] = Field(default=None, sa_column=Column("2_hero_id", Float))
    c3_hero_id: Optional[float] = Field(default=None, sa_column=Column("3_hero_id", Float))
    c4_hero_id: Optional[float] = Field(default=None, sa_column=Column("4_hero_id", Float))
    c128_hero_id: Optional[float] = Field(default=None, sa_column=Column("128_hero_id", Float))
    c129_hero_id: Optional[float] = Field(default=None, sa_column=Column("129_hero_id", Float))
    c130_hero_id: Optional[float] = Field(default=None, sa_column=Column("130_hero_id", Float))
    c131_hero_id: Optional[float] = Field(default=None, sa_column=Column("131_hero_id", Float))
    c132_hero_id: Optional[float] = Field(default=None, sa_column=Column("132_hero_id", Float))
    
    # Columns for account IDs:
    c0_account_id: Optional[float] = Field(default=None, sa_column=Column("0_account_id", Float))
    c1_account_id: Optional[float] = Field(default=None, sa_column=Column("1_account_id", Float))
    c2_account_id: Optional[float] = Field(default=None, sa_column=Column("2_account_id", Float))
    c3_account_id: Optional[float] = Field(default=None, sa_column=Column("3_account_id", Float))
    c4_account_id: Optional[float] = Field(default=None, sa_column=Column("4_account_id", Float))
    c128_account_id: Optional[float] = Field(default=None, sa_column=Column("128_account_id", Float))
    c129_account_id: Optional[float] = Field(default=None, sa_column=Column("129_account_id", Float))
    c130_account_id: Optional[float] = Field(default=None, sa_column=Column("130_account_id", Float))
    c131_account_id: Optional[float] = Field(default=None, sa_column=Column("131_account_id", Float))
    c132_account_id: Optional[float] = Field(default=None, sa_column=Column("132_account_id", Float))
    
    radiant_name: Optional[str] = Field(default=None, sa_column=Column("radiant_name", Text))
    radiant_team_id: Optional[float] = Field(default=None, sa_column=Column("radiant_team_id", Float))
    dire_name: Optional[str] = Field(default=None, sa_column=Column("dire_name", Text))
    dire_team_id: Optional[float] = Field(default=None, sa_column=Column("dire_team_id", Float))
    start_time: Optional[int] = Field(default=None, sa_column=Column("start_time", BigInteger))
    duration: Optional[int] = Field(default=None, sa_column=Column("duration", BigInteger))
    radiant_win: Optional[bool] = Field(default=None, sa_column=Column("radiant_win", Boolean))
    match_id: int = Field(default=None, sa_column=Column("match_id", BigInteger, primary_key=True))
    
    __table_args__ = (UniqueConstraint("match_id", name="unique_match_id_constraint"),)

class ProMatchID(SQLModel, table=True):
    # Transient table, serving as checkpoint for fetching match_details using pro matches match_id
    __tablename__ = "pro_matches_id"
    
    match_id: int = Field(sa_column=Column(BigInteger, primary_key=True, autoincrement=False))
