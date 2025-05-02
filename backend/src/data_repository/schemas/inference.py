from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger
from datetime import datetime

class MatchPredictionTable(SQLModel, table=True):
    __tablename__ = 'match_predictions'
    
    # Composite Primary Key
    match_id: int = Field(sa_type=BigInteger, primary_key=True, 
                          foreign_key="matches.match_id")
    predictor_name: str = Field(primary_key=True, index=True)
    
    prediction: bool
    predictor_version: str = Field(default=None)
    prediction_date: datetime 
    prediction_probability: float = Field(default=None)
