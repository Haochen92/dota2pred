from sqlmodel import SQLModel, Field
from .schema import LeagueItem

class LeagueTable(SQLModel, LeagueItem, table=True): # type: ignore
    # overrides LeagueItem
    leagueid: int = Field(primary_key=True)