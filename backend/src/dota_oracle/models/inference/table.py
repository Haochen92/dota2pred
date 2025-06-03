from sqlmodel import Field, Relationship
from sqlalchemy import BigInteger, Column, TIMESTAMP
from datetime import datetime

from .schema import MatchPrediction

class MatchPredictionTable(MatchPrediction, table=True):
    __tablename__ = 'match_predictions' # type: ignore
    
    # Override Composite Primary Key
    match_id: int = Field(sa_type=BigInteger, foreign_key="matches.match_id", primary_key=True)
    predictor_name: str = Field(primary_key=True, index=True)
    
    # Override datetime with timezone
    prediction_date: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), index=True, nullable=False)
    )
    
    # Relationship
    match: "MatchTable" = Relationship(back_populates="predictions")
    

