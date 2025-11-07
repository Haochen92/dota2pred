from pydantic import BaseModel, Field
from sqlmodel import SQLModel
from typing import List, Optional
from datetime import datetime


"""
###############
# MODEL METADATA
################
"""


# API responses
class PerformanceMetrics(BaseModel):
    """Model performance metrics container.

    Attributes:
        accuracy: Classification accuracy (float)
        roc_auc: ROC AUC score metric (float)
        log_loss: Log loss metric (float)
    """

    accuracy: Optional[float] = None
    roc_auc: Optional[float] = None
    log_loss: Optional[float] = None


class TrainingDataSummary(BaseModel):
    """Summary statistics of the training data.

    Attributes:
        source: source of training data (str)
        num_features: Number of features used (int)
        class_distribution: Distribution of target classes (dict)
    """

    source_description: str = ""
    splitting_strategy: str = ""
    total_match_counts: int = 0
    start_match_id: int = 0
    end_match_id: int = 0
    start_date: datetime = datetime.now()
    end_date: datetime = datetime.now()


class VersionMetaData(BaseModel):
    """Version metadata for model releases.

    Attributes:
        changes: List of changes in this version (List[str])
        performance_metrics: Performance metrics for this version (PerformanceMetrics)
    """

    changes: List[str] = []
    performance_metrics: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    feature_columns: List[str] = []
    training_summary: TrainingDataSummary = Field(default_factory=TrainingDataSummary)


class ModelMetaData(BaseModel):
    """Model Metadata Schema.

    Attributes:
        name: Model name (str)
        version: Current version (str)
        trained_date: Model training date (datetime)
        feature_columns: List of feature column names (List[str])
        previous_version: Previous model version (str)
        version_metadata: Version-specific metadata (VersionMetaData)
    """

    name: str
    description: Optional[str] = ""
    intended_use: Optional[str] = ""
    limitations: Optional[str] = ""
    version: str
    trained_date: datetime
    previous_version: str = ""
    version_metadata: VersionMetaData = Field(default_factory=VersionMetaData)


"""
###############
# API RESPONSE MODELS
################
"""


class ModelMetaDataAPIResponse(ModelMetaData):
    """API response for model metadata information.

    Attributes:
        name: Model name (str)
        version: Current version (str)
        trained_date: Model training date (datetime)
        feature_columns: List of feature column names (List[str])
        previous_version: Previous model version (str)
        version_metadata: Version-specific metadata (VersionMetaData)
    """


class ModelPredictionAPIResponse(BaseModel):
    """API response for model predictions.

    Attributes:
        prediction: Prediction results (List[int])
        probability: Prediction probabilities (Optional[List[float]])
    """

    prediction: List[int]
    probability: Optional[List[float]] = []


# DTO
class MatchPrediction(SQLModel):
    """DTO for match prediction data.

    Attributes:
        match_id: Match identifier (int)
        predictor_name: Name of the predictor model (str)
        prediction: Prediction result (Optional[bool])
        prediction_probability: Confidence score 0-1 (Optional[float])
        predictor_version: Model version used (str)
        prediction_date: When prediction was made (datetime)
    """

    match_id: int
    predictor_name: str

    prediction: Optional[bool]
    prediction_probability: Optional[float] = Field(ge=0.0, le=1.0)

    predictor_version: str = Field(default="v1.0")
    prediction_date: datetime


class PredictionInputPayload(BaseModel):
    input_features: List[List[float]]
