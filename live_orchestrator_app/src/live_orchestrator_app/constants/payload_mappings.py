from typing import Dict, Type

from dota_oracle_common.constants.redis_constants import (
    STREAM_NEW_MATCHES,
    STREAM_PENDING_PREDICTION,
    STREAM_PENDING_COMPLETION,
)
from dota_oracle_common.models.redis.schema import (
    FeatureEngineeringPayload,
    PredictionPayload,
    CompletionPayload,
    PayloadModel,
)

PAYLOAD_MODEL_MAPPING: Dict[str, Type[PayloadModel]] = {
    STREAM_NEW_MATCHES: FeatureEngineeringPayload,
    STREAM_PENDING_PREDICTION: PredictionPayload,
    STREAM_PENDING_COMPLETION: CompletionPayload,
}
