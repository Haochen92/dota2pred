from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PerformanceMetrics(BaseModel):
    accuracy: float = 0.0
    f1_score: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    
class VersionChanges(BaseModel):
    changes: List[str] = []
    performance_metrics: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    training_data: str = ""
    
class ModelMetaData(BaseModel):
    model_name: str
    version: str
    trained_date: datetime
    previous_version : str = ""
    changes: VersionChanges = Field(default_factory=VersionChanges)