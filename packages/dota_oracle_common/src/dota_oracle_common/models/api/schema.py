from pydantic import BaseModel
from ..match.schema import MatchNotifcationAPIPayload, CompletedMatchAPIPayload
from typing import List


class LiveStateUpdateRequest(BaseModel):
    live_matches: List[MatchNotifcationAPIPayload]


class CompletedMatchRequest(BaseModel):
    completed_matches: List[CompletedMatchAPIPayload]
