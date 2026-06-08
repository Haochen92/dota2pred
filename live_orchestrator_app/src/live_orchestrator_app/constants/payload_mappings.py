from typing import Dict, Type

from dota_oracle_common.constants.redis_constants import (
    STREAM_NEW_MATCHES,
    STREAM_PENDING_PREDICTION,
    STREAM_PENDING_COMPLETION,
    STREAM_PENDING_ODDS,
)
from dota_oracle_common.models.redis.schema import (
    FeatureEngineeringPayload,
    PredictionPayload,
    CompletionPayload,
    OddsPayload,
    PayloadModel,
)

PAYLOAD_MODEL_MAPPING: Dict[str, Type[PayloadModel]] = {
    STREAM_NEW_MATCHES: FeatureEngineeringPayload,
    STREAM_PENDING_PREDICTION: PredictionPayload,
    STREAM_PENDING_COMPLETION: CompletionPayload,
    STREAM_PENDING_ODDS: OddsPayload,
}
