from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON
from typing import List
from .schema import HeroData

class HeroDataTable(HeroData, SQLModel, table=True):
    
    # HeroData Model overrides
    id: int = Field(primary_key=True)
    roles: List[str] = Field(default=[], sa_column=Column(JSON))