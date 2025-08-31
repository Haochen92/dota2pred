from pydantic import BaseModel, Field, model_validator
from ..match.schema import MatchNotifcationAPIPayload, CompletedMatchAPIPayload
from typing import List, Optional, Annotated


class LiveStateUpdateRequest(BaseModel):
    live_matches: List[MatchNotifcationAPIPayload]


class CompletedMatchRequest(BaseModel):
    completed_matches: List[CompletedMatchAPIPayload]


# Model for public match prediction request
HeroId = Annotated[int, Field(ge=1, le=150)]


class PublicMatchPredictionRequest(BaseModel):
    radiant_hero_id_1: HeroId
    radiant_hero_id_2: HeroId
    radiant_hero_id_3: HeroId
    radiant_hero_id_4: HeroId
    radiant_hero_id_5: HeroId
    dire_hero_id_1: HeroId
    dire_hero_id_2: HeroId
    dire_hero_id_3: HeroId
    dire_hero_id_4: HeroId
    dire_hero_id_5: HeroId

    @model_validator(mode="after")
    def validate_no_duplicate_heroes(self):
        hero_ids = [
            self.radiant_hero_id_1,
            self.radiant_hero_id_2,
            self.radiant_hero_id_3,
            self.radiant_hero_id_4,
            self.radiant_hero_id_5,
            self.dire_hero_id_1,
            self.dire_hero_id_2,
            self.dire_hero_id_3,
            self.dire_hero_id_4,
            self.dire_hero_id_5,
        ]
        if len(hero_ids) != len(set(hero_ids)):
            raise ValueError("Duplicate heroes are not allowed in a match")
        return self


class PublicMatchPredictionResponse(BaseModel):
    prediction: bool
    probability: Annotated[Optional[float], Field(ge=0.0, le=1.0)]


# Hero Image Routes
class HeroImageData(BaseModel):
    hero_id: int
    hero_name: str
    image_url: Optional[str] = None
    icon_url: Optional[str] = None
    primary_attr: Optional[str] = None


class HeroImageResponse(BaseModel):
    heroes: List[HeroImageData]
