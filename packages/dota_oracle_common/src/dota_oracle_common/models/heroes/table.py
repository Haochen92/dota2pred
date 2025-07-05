from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import List
from .schema import HeroData


class HeroDataTable(HeroData, SQLModel, table=True):
    """Database table for hero data.

    Inherits from HeroData with database-specific overrides.

    Attributes:
        id: Primary key hero identifier (int)
        roles: Hero roles stored as JSON (List[str])
    """

    # HeroData Model overrides
    id: int = Field(primary_key=True)
    roles: List[str] = Field(default=[], sa_column=Column(JSON))
