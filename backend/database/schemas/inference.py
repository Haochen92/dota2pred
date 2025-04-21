from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column
from datetime import datetime

class MatchPrediction(SQLModel, table=True):
    __tablename__ = 'match_predictions'
    
    # Primary Key
    match_id: int = Field(default=None,sa_column=Column('match_id', BigInteger, primary_key=True))
    
    prediction: bool
    model_name: str = Field(default=None)
    model_version: str = Field(default=None)
    prediction_date: datetime = Field(default_factory=datetime.now)
