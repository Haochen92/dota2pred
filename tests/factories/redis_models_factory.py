from polyfactory.factories.pydantic_factory import ModelFactory
from dota_oracle_common.models.redis.schema import (
    StreamEvent,
    FeatureEngineeringPayload,
    PredictionPayload,
    CompletionPayload,
    CompletedMatchPayload,
    EventToPublish,
    ConsumedEvent,
    MatchStatusValue,
    FailureRecord,
)

from polyfactory import Use

from polyfactory.pytest_plugin import register_fixture


@register_fixture
class StreamMatchEventFactory(ModelFactory[StreamEvent[FeatureEngineeringPayload]]):
    """
    Factory for the generic StreamEvent DTO.

    By default, it creates a StreamEvent[FeatureEngineeringPayload] variation.
    To create other variations, override the `payload` field during the build() call.

    Example:
        prediction_payload = PredictionPayloadFactory.build()
        stream_event = StreamEventFactory.build(payload=prediction_payload)
    """

    pass


@register_fixture
class EventToPublishFactory(ModelFactory[EventToPublish[FeatureEngineeringPayload]]):
    """
    Factory for the generic EventToPublish DTO.

    By default, it creates a EventToPublish[FeatureEngineeringPayload] variation.
    To create other variations, override the `payload` field during the build() call.

    Example:
        prediction_payload = PredictionPayloadFactory.build()
        stream_event = EventToPublishFactory.build(payload=prediction_payload)
    """

    pass


@register_fixture
class ConsumedEventFactory(ModelFactory[ConsumedEvent[FeatureEngineeringPayload]]):
    """
    Factory for the generic ConsumedEvent DTO.

    By default, it creates a ConsumedEvent[FeatureEngineeringPayload] variation.
    To create other variations, override the `payload` field during the build() call.

    Example:
        prediction_payload = PredictionPayloadFactory.build()
        stream_event = ConsumedEventFactory.build(payload=prediction_payload)
    """

    pass


@register_fixture
class MatchStatusValueFactory(ModelFactory[MatchStatusValue]):
    pass


@register_fixture
class FailureRecordFactory(ModelFactory[FailureRecord[FeatureEngineeringPayload]]):
    """
    Factory for the generic FailureRecord DTO.

    By default, it creates a FailureRecord[FeatureEngineeringPayload] variation.
    To create other variations, override the `payload` field during the build() call.

    Example:
        prediction_payload = PredictionPayloadFactory.build()
        stream_event = FailureRecordFactory.build(payload=prediction_payload)
    """

    pass


@register_fixture
class FeatureEngineeringPayloadFactory(ModelFactory[FeatureEngineeringPayload]):
    pass


@register_fixture
class PredictionPayloadFactory(ModelFactory[PredictionPayload]):
    pass


@register_fixture
class CompletionPayloadFactory(ModelFactory[CompletionPayload]):
    pass


@register_fixture
class CompletedMatchPayloadFactory(ModelFactory[CompletedMatchPayload]):
    outcome = Use(lambda: True)
