from sqlmodel import SQLModel, Field
from dota_oracle.pydantic_models.leagues import LeagueItem

class LeagueTable(SQLModel, LeagueItem, table=True): # type: ignore
    # overrides LeagueItem
    leagueid: int = Field(primary_key=True)