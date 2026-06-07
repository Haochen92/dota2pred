from pydantic import BaseModel, Field, model_validator
from enum import IntEnum

from ..match.schema import MatchNotifcationAPIPayload, CompletedMatchAPIPayload
from ..features.schema import AllFeaturesDTO
from ..inference.schema import MatchPrediction

from typing import List, Optional, Annotated, Dict
from datetime import datetime


class LiveStateUpdateRequest(BaseModel):
    live_matches: List[MatchNotifcationAPIPayload]


class CompletedMatchRequest(BaseModel):
    completed_matches: List[CompletedMatchAPIPayload]


# Model for public match prediction request
HeroId = Annotated[int, Field(ge=1)]


class PublicMatchPredictionRequest(BaseModel):
    # Prefer list-based input (order does not matter to the model)
    radiant_heroes: List[HeroId] = Field(..., min_length=5, max_length=5)
    dire_heroes: List[HeroId] = Field(..., min_length=5, max_length=5)

    # No backward-compatibility coercion; frontend must send list fields.

    @model_validator(mode="after")
    def validate_no_duplicate_heroes(self):
        all_heroes = self.radiant_heroes + self.dire_heroes
        if len(all_heroes) != len(set(all_heroes)):
            raise ValueError("Duplicate heroes are not allowed in a match")
        return self


class PublicMatchPredictionDTO(PublicMatchPredictionRequest):
    match_id: int
    start_time: datetime

    def to_feature_dict(self) -> Dict[str, int]:
        """
        Transforms the DTO into a flat dictionary with slot_*_hero_id keys
        as expected by the feature engineering process.
        """
        feature_dict: Dict[str, int] = {
            "match_id": self.match_id,
        }

        # Radiant slots 0-4 from list order
        for i, hero_id in enumerate(self.radiant_heroes):
            feature_dict[f"slot_{i}_hero_id"] = hero_id

        # Dire slots 128-132 from list order
        for i, hero_id in enumerate(self.dire_heroes):
            feature_dict[f"slot_{128 + i}_hero_id"] = hero_id

        return feature_dict


class PublicMatchPredictionResponse(BaseModel):
    prediction: bool
    probability: Annotated[Optional[float], Field(ge=0.0, le=1.0)]


# Model History endpoint
class HistoryRange(IntEnum):
    week = 7
    month = 30
    quarter = 90
    year = 365
    all_time = 0


class AggregateBy(IntEnum):
    day = 1
    week = 7
    month = 30


class ModelHistoryRequest(BaseModel):
    history_range: HistoryRange
    aggregate_by: AggregateBy


class ConfidenceBin(BaseModel):
    bin_name: str
    match_count: int
    bin_accuracy: Optional[float]
    average_confidence: Optional[float]


class CalibrationPlot(BaseModel):
    bins: List[ConfidenceBin] = Field(default_factory=list)


class ModelPerformanceEntry(BaseModel):
    date: datetime
    accuracy: float
    auc: float
    root_brier: float
    match_count: int


class ModelHistoryResponse(BaseModel):
    history: List[ModelPerformanceEntry]
    calibration_plot: CalibrationPlot


# Hero Image Routes
class HeroImageData(BaseModel):
    hero_id: int
    hero_name: str
    image_url: Optional[str] = None
    icon_url: Optional[str] = None
    primary_attr: Optional[str] = None


class HeroImageResponse(BaseModel):
    heroes: List[HeroImageData]


# Patches Routes
class PatchDataAPIResponse(BaseModel):
    """API response model for available patch identifiers."""

    patches: List[str] = []


# Leagues Routes
class LeagueData(BaseModel):
    leagueid: int
    tier: Optional[str] = None
    name: Optional[str] = None


class LeagueDataResponse(BaseModel):
    leagues: List[LeagueData]


class PredictionDetailsResponse(BaseModel):
    features: Optional[AllFeaturesDTO]
    prediction_details: Optional[MatchPrediction]


class PredictionDetailsRequest(BaseModel):
    match_id: int
