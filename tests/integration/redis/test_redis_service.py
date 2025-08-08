import pytest
from redis.asyncio import Redis as AIORedis
from typing import Set, List, Type
import json
from datetime import datetime, timedelta, timezone

from dota_oracle_common.utils.time_utils import get_current_utc_iso_timestamp

from dota_oracle_common.models.redis.schema import (
    FailureRecord,
    ConsumedEvent,
    EventToPublish,
    MatchProcessingStatus,
    FeatureEngineeringPayload,
    PredictionPayload,
    CompletionPayload,
    PayloadModel,
)
from dota_oracle_common.constants.redis_constants import (
    MATCH_SET,
    MATCH_STATUS,
    TMP_KEY,
    STREAM_NEW_MATCHES,
    STREAM_PENDING_PREDICTION,
    STREAM_PENDING_COMPLETION,
    FEATURE_ENGINEER_GROUP,
    PREDICTION_GROUP,
    COMPLETION_GROUP,
    FAILED_EVENTS_MAPPING,
)

from live_orchestrator_app.redis_services.redis_service import RedisService

# Import factory fixtures
from ...factories.redis_models_factory import (
    FeatureEngineeringPayloadFactory,
    PredictionPayloadFactory,
    CompletionPayloadFactory,
    ConsumedEventFactory,
    FailureRecordFactory,
)

from ...factories.repository_factories import MatchTableFactory

from .redis_service_scenarios import (
    UPDATE_LIVE_MATCH_SCENARIOS_ARGS,
    UPDATE_LIVE_MATCH_SCENARIOS,
    PUBLISH_NEW_MATCH_SCENARIOS_ARGS,
    PUBLISH_NEW_MATCH_SCENARIOS,
    PUBLISH_FEATURES_SCENARIOS_ARGS,
    PUBLISH_FEATURES_SCENARIOS,
    PUBLISH_PREDICTION_SCENARIOS_ARGS,
    PUBLISH_PREDICTION_SCENARIOS,
    FETCH_MATCHES_SCENARIOS_ARGS,
    FETCH_MATCHES_SCENARIOS,
    FAILURE_RECORD_SCENARIO_ARGS,
    FAILURE_RECORD_SCENARIO,
)

from pydantic import BaseModel

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_stream_with_event(redis_client: AIORedis, stream_name: str, match_id: int, payload: BaseModel) -> str:
    """Helper to create and add an event to a stream using the flattened data model."""
    EventModel = EventToPublish[type(payload)]
    event_to_publish = EventModel(match_id=match_id, payload=payload)

    event_dict = event_to_publish.model_dump(mode="json")
    event_dict["payload"] = payload.model_dump_json()

    return await redis_client.xadd(stream_name, event_dict)  # type: ignore


def _create_old_event_id(seconds_in_past: int) -> str:
    """Creates a Redis stream ID that appears to be from the past."""
    past_timestamp = datetime.now(timezone.utc) - timedelta(seconds=seconds_in_past)
    timestamp_ms = int(past_timestamp.timestamp() * 1000)
    return f"{timestamp_ms}-0"


async def test_initialize_redis_service(redis_service_test_subject: RedisService, test_redis_client: AIORedis) -> None:
    """Tests that consumer groups and streams are created idempotently."""
    await redis_service_test_subject.initialize_async_service()

    expected_streams_and_groups = [
        (STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP),
        (STREAM_PENDING_PREDICTION, PREDICTION_GROUP),
        (STREAM_PENDING_COMPLETION, COMPLETION_GROUP),
    ]

    for stream_name, group_name in expected_streams_and_groups:
        groups_info = await test_redis_client.xinfo_groups(stream_name)
        assert any(
            group_info["name"] == group_name for group_info in groups_info
        ), f"Consumer group '{group_name}' not found for stream '{stream_name}'"
        assert await test_redis_client.exists(stream_name), f"Stream '{stream_name}' was not created."


@pytest.mark.parametrize(UPDATE_LIVE_MATCH_SCENARIOS_ARGS, UPDATE_LIVE_MATCH_SCENARIOS)
async def test_update_live_match_set_and_get_new(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    test_id: str,
    initial_redis_match_set: Set[int],
    input_current_ids: List[int],
    expected_new_ids_returned: Set[int],
    expected_final_redis_match_set: Set[int],
) -> None:
    """Tests the atomic update of the live match set."""
    await test_redis_client.delete(MATCH_SET, TMP_KEY)
    if initial_redis_match_set:
        await test_redis_client.sadd(MATCH_SET, *[str(id_val) for id_val in initial_redis_match_set])  # type: ignore

    returned_new_ids = await redis_service_test_subject.update_live_match_set_and_get_new(input_current_ids)
    assert returned_new_ids == expected_new_ids_returned, f"Test ID '{test_id}': Incorrect set of new IDs returned."

    actual_final_redis_match_set_str = await test_redis_client.smembers(MATCH_SET)  # type: ignore
    actual_final_redis_match_set = {int(val) for val in actual_final_redis_match_set_str}
    assert (
        actual_final_redis_match_set == expected_final_redis_match_set
    ), f"Test ID '{test_id}': Incorrect final state of MATCH_SET."


@pytest.mark.parametrize(PUBLISH_NEW_MATCH_SCENARIOS_ARGS, PUBLISH_NEW_MATCH_SCENARIOS)
async def test_publish_new_match_to_feature_eng(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    match_table_factory: MatchTableFactory,
    test_id: str,
    match_id: int,
    expected_return_value: bool,
) -> None:
    """Tests publishing a brand new match to the first stage of the pipeline."""
    match_status_key = f"{MATCH_STATUS}:{match_id}"
    await test_redis_client.delete(match_status_key)
    await test_redis_client.xtrim(STREAM_NEW_MATCHES, maxlen=0)

    match_details = match_table_factory.build(match_id=match_id)
    actual_return_value = await redis_service_test_subject.publish_new_match_to_feature_eng(match_details)

    assert actual_return_value == expected_return_value

    if expected_return_value:
        stream_entries = await test_redis_client.xrevrange(STREAM_NEW_MATCHES, count=1)
        assert len(stream_entries) > 0, "No entry found in stream after successful publish."

        _, event_data_dict = stream_entries[0]

        assert "match_id" in event_data_dict
        assert "payload" in event_data_dict

        assert event_data_dict["match_id"] == str(match_id)

        # Check the payload by parsing its JSON string
        parsed_payload = json.loads(event_data_dict["payload"])
        assert "match_details" in parsed_payload


@pytest.mark.parametrize(PUBLISH_FEATURES_SCENARIOS_ARGS, PUBLISH_FEATURES_SCENARIOS)
async def test_publish_features_to_prediction(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    feature_engineering_payload_factory: FeatureEngineeringPayloadFactory,
    prediction_payload_factory: PredictionPayloadFactory,
    test_id: str,
    match_id: int,
    expected_return_val: bool,
) -> None:
    """Tests advancing a match from Feature Engineering to Prediction."""
    match_status_key = f"{MATCH_STATUS}:{match_id}"
    await test_redis_client.delete(match_status_key)
    await test_redis_client.xtrim(STREAM_NEW_MATCHES, maxlen=0)
    await test_redis_client.xtrim(STREAM_PENDING_PREDICTION, maxlen=0)

    seed_payload = feature_engineering_payload_factory.build()
    event_id_to_ack = await _seed_stream_with_event(test_redis_client, STREAM_NEW_MATCHES, match_id, seed_payload)
    await test_redis_client.xreadgroup(FEATURE_ENGINEER_GROUP, "test-consumer", {STREAM_NEW_MATCHES: event_id_to_ack})

    features_payload = prediction_payload_factory.build()
    actual_return_val = await redis_service_test_subject.publish_features_to_prediction(
        match_id=match_id, features=features_payload, event_id_to_ack=event_id_to_ack
    )

    assert actual_return_val == expected_return_val

    actual_match_status = await test_redis_client.hget(match_status_key, "status")  # type: ignore
    assert actual_match_status == MatchProcessingStatus.PENDING_PREDICTION.value

    stream_entries = await test_redis_client.xrevrange(STREAM_PENDING_PREDICTION, count=1)
    assert len(stream_entries) == 1
    _, event_data_dict = stream_entries[0]

    assert "match_id" in event_data_dict
    assert event_data_dict["match_id"] == str(match_id)
    assert "payload" in event_data_dict

    parsed_payload = json.loads(event_data_dict["payload"])
    assert parsed_payload["hero_features"] is not None

    pending = await test_redis_client.xpending_range(
        STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP, min="-", max="+", count=10
    )
    assert not any(p["message_id"] == event_id_to_ack for p in pending), "Message was not ACKed."


@pytest.mark.parametrize(PUBLISH_PREDICTION_SCENARIOS_ARGS, PUBLISH_PREDICTION_SCENARIOS)
async def test_publish_prediction_to_completion(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    prediction_payload_factory: PredictionPayloadFactory,
    completion_payload_factory: CompletionPayloadFactory,
    test_id: str,
    match_id: int,
    expected_return_val: bool,
) -> None:
    """Tests advancing a match from Prediction to Completion."""
    match_status_key = f"{MATCH_STATUS}:{match_id}"
    await test_redis_client.delete(match_status_key)
    await test_redis_client.xtrim(STREAM_PENDING_PREDICTION, maxlen=0)
    await test_redis_client.xtrim(STREAM_PENDING_COMPLETION, maxlen=0)

    seed_payload = prediction_payload_factory.build()
    event_id_to_ack = await _seed_stream_with_event(
        test_redis_client, STREAM_PENDING_PREDICTION, match_id, seed_payload
    )
    await test_redis_client.xreadgroup(PREDICTION_GROUP, "test-consumer", {STREAM_PENDING_PREDICTION: event_id_to_ack})

    completion_payload = completion_payload_factory.build(match_id=match_id)
    actual_return_val = await redis_service_test_subject.publish_prediction_to_completion(
        match_id=match_id, prediction=completion_payload, event_id_to_ack=event_id_to_ack
    )

    assert actual_return_val == expected_return_val

    actual_match_status = await test_redis_client.hget(match_status_key, "status")  # type: ignore
    assert actual_match_status == MatchProcessingStatus.PENDING_COMPLETION.value

    stream_entries = await test_redis_client.xrevrange(STREAM_PENDING_COMPLETION, count=1)
    assert len(stream_entries) == 1
    _, event_data_dict = stream_entries[0]

    ### CORRECTED: Verify the new flattened structure
    assert "match_id" in event_data_dict
    assert event_data_dict["match_id"] == str(match_id)
    assert "payload" in event_data_dict

    parsed_payload = json.loads(event_data_dict["payload"])
    assert parsed_payload["radiant_win"] is not None

    pending = await test_redis_client.xpending_range(
        STREAM_PENDING_PREDICTION, PREDICTION_GROUP, min="-", max="+", count=10
    )
    assert not any(p["message_id"] == event_id_to_ack for p in pending), "Message was not ACKed."


@pytest.mark.parametrize(FETCH_MATCHES_SCENARIOS_ARGS, FETCH_MATCHES_SCENARIOS)
async def test_fetch_events(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    feature_engineering_payload_factory: FeatureEngineeringPayloadFactory,
    prediction_payload_factory: PredictionPayloadFactory,
    completion_payload_factory: CompletionPayloadFactory,
    test_id: str,
    method_to_call: str,
    stream_to_fetch_from: str,
    consumer_group: str,
    payload_type_to_seed: Type[PayloadModel],
    expected_payload_type: Type[PayloadModel],
    input_match_ids: List[int],
    consumer_name: str,
    fetch_count: int,
    expected_match_ids: Set[int],
) -> None:
    """
    ### NO CHANGE NEEDED HERE. This test is robust.
    # By fixing the `_seed_stream_with_event` helper, this test now correctly
    # sets up the state with the new data format. The assertions operate on the
    # final Pydantic object returned by the fetch method, which is the correct
    # level of abstraction. This test validates the behavior, not the implementation.
    """
    payload_factories = {
        FeatureEngineeringPayload: feature_engineering_payload_factory,
        PredictionPayload: prediction_payload_factory,
        CompletionPayload: completion_payload_factory,
    }
    seeding_factory = payload_factories[payload_type_to_seed]

    await test_redis_client.xtrim(stream_to_fetch_from, maxlen=0)

    if input_match_ids:
        for match_id in input_match_ids:
            payload = seeding_factory.build()
            await _seed_stream_with_event(test_redis_client, stream_to_fetch_from, match_id, payload)

    try:
        await test_redis_client.xgroup_destroy(stream_to_fetch_from, consumer_group)
    except Exception:
        pass

    try:
        await test_redis_client.xgroup_create(stream_to_fetch_from, consumer_group, id="0", mkstream=True)
    except Exception:
        pass

    fetched_events: List[ConsumedEvent] = await getattr(redis_service_test_subject, method_to_call)(
        consumer=consumer_name, count=fetch_count
    )

    assert len(fetched_events) == len(expected_match_ids)
    actual_match_ids = {event.match_id for event in fetched_events}
    assert actual_match_ids == expected_match_ids

    for event in fetched_events:
        assert isinstance(event, ConsumedEvent)
        assert isinstance(event.payload, expected_payload_type)


@pytest.mark.parametrize(FAILURE_RECORD_SCENARIO_ARGS, FAILURE_RECORD_SCENARIO)
async def test_record_failure_and_ack(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    consumed_event_factory: ConsumedEventFactory,
    failure_record_factory: FailureRecordFactory,
    test_id: str,
    test_stream_input: str,
    test_original_group: str,
) -> None:
    """Tests that failed events are recorded to a DLQ and ACKed."""
    target_dlq_hash = FAILED_EVENTS_MAPPING.get(test_stream_input)
    if target_dlq_hash:
        await test_redis_client.delete(target_dlq_hash)

    try:
        await test_redis_client.xgroup_create(test_stream_input, test_original_group, mkstream=True, id="0")
    except Exception:
        pass

    original_event_id = await _seed_stream_with_event(
        test_redis_client, test_stream_input, 123, PredictionPayloadFactory().build()
    )
    await test_redis_client.xreadgroup(test_original_group, "test-consumer", {test_stream_input: original_event_id})

    consumed_event = consumed_event_factory.build(event_id=original_event_id, match_id=123)

    failure_record = failure_record_factory.build(
        original_group=test_original_group,
        original_stream=test_stream_input,
        original_data=consumed_event,  # This now contains a Pydantic object
        original_event_id=original_event_id,
    )

    actual_return_value = await redis_service_test_subject._record_failure_and_ack(failure_record)

    if not target_dlq_hash:
        assert not actual_return_value
    else:
        assert actual_return_value
        stored_data = await test_redis_client.hget(target_dlq_hash, original_event_id)  # type: ignore
        assert stored_data is not None

        # Verify the structure of the stored failure record
        parsed_failure_record = json.loads(stored_data)
        assert parsed_failure_record["original_event_id"] == original_event_id
        assert parsed_failure_record["original_data"]["match_id"] == 123

        pending = await test_redis_client.xpending_range(
            test_stream_input, test_original_group, min="-", max="+", count=10
        )
        assert not any(p["message_id"] == original_event_id for p in pending), "Message was not ACKed."


async def test_record_failure_and_ack_serialization_error(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    consumed_event_factory: ConsumedEventFactory,
    failure_record_factory: FailureRecordFactory,
    mocker,
) -> None:
    """Tests that a fallback is stored if the FailureRecord itself fails to serialize."""
    original_stream = STREAM_PENDING_PREDICTION
    original_group = PREDICTION_GROUP
    target_dlq_hash = FAILED_EVENTS_MAPPING[original_stream]

    await test_redis_client.delete(target_dlq_hash)
    await test_redis_client.xtrim(original_stream, maxlen=0)
    original_event_id = await _seed_stream_with_event(
        test_redis_client, original_stream, 456, PredictionPayloadFactory().build()
    )
    await test_redis_client.xreadgroup(original_group, "test-consumer", {original_stream: original_event_id})

    consumed_event = consumed_event_factory.build(event_id=original_event_id, match_id=456)

    test_failure_record = failure_record_factory.build(
        original_group=original_group,
        original_stream=original_stream,
        original_data=consumed_event,
        original_event_id=original_event_id,
    )

    mocker.patch.object(FailureRecord, "model_dump_json", side_effect=TypeError("Serialization failed"))

    actual_return_value = await redis_service_test_subject._record_failure_and_ack(test_failure_record)
    assert actual_return_value

    stored_fallback_json = await test_redis_client.hget(target_dlq_hash, original_event_id)  # type: ignore
    assert stored_fallback_json is not None
    fallback_data = json.loads(stored_fallback_json)
    assert fallback_data["error"] == "DLQ data serialization failed"
    assert fallback_data["original_event_id"] == original_event_id

    pending_after_ack = await test_redis_client.xpending_range(
        original_stream, original_group, min="-", max="+", count=1
    )
    assert not any(
        p["message_id"] == original_event_id for p in pending_after_ack
    ), "Message was not ACKed after serialization failure."


class TestRedisJanitorService:
    """
    Integration tests for the Janitor/recovery functionality of the RedisService,
    specifically for handling expired or stale events.
    """

    STREAM_NAME = STREAM_PENDING_COMPLETION
    GROUP_NAME = COMPLETION_GROUP
    CONSUMER_1 = "test_consumer_alpha"
    JANITOR_CONSUMER = "janitor_worker_001"

    async def test_fetch_expired_events(
        self,
        redis_service_test_subject: RedisService,
        test_redis_client: AIORedis,
        completion_payload_factory: CompletionPayloadFactory,
    ):
        """
        Tests that fetch_expired_events correctly identifies events older than
        the specified duration based on their creation timestamp.
        """
        # ARRANGE - Complete cleanup for isolation
        try:
            await test_redis_client.xgroup_destroy(self.STREAM_NAME, self.GROUP_NAME)
        except Exception:
            pass
        try:
            await test_redis_client.delete(self.STREAM_NAME)  # Complete stream deletion
        except Exception:
            pass
        await test_redis_client.xgroup_create(self.STREAM_NAME, self.GROUP_NAME, id="0", mkstream=True)

        # --- Seed Events with specific timestamps ---
        old_id = _create_old_event_id(seconds_in_past=2000)  # Will be expired (older than 1800s)
        recent_id = _create_old_event_id(seconds_in_past=200)  # Will not be expired

        payload = completion_payload_factory.build()
        payload_2 = completion_payload_factory.build()

        await test_redis_client.xadd(
            self.STREAM_NAME, {"payload": payload.model_dump_json(), "match_id": "100"}, id=old_id
        )
        await test_redis_client.xadd(
            self.STREAM_NAME, {"payload": payload_2.model_dump_json(), "match_id": "200"}, id=recent_id
        )

        await test_redis_client.xreadgroup(self.GROUP_NAME, self.CONSUMER_1, {self.STREAM_NAME: ">"}, count=2)
        expired_ids = await redis_service_test_subject.fetch_expired_events(
            stream_name=self.STREAM_NAME, consumer_group=self.GROUP_NAME, duration=1800
        )
        assert len(expired_ids) == 1
        assert expired_ids[0] == old_id
        assert recent_id not in expired_ids

    async def test_claim_and_parse_expired_events(
        self,
        redis_service_test_subject: RedisService,
        test_redis_client: AIORedis,
        completion_payload_factory: CompletionPayloadFactory,
    ):
        """
        Tests the full workflow:
        1. Identify expired event IDs.
        2. Claim those events, which transfers ownership and returns their content.
        3. Parse the claimed events back into Pydantic models.
        """
        # ARRANGE - Complete cleanup for isolation
        try:
            await test_redis_client.xgroup_destroy(self.STREAM_NAME, self.GROUP_NAME)
        except Exception:
            pass
        try:
            await test_redis_client.delete(self.STREAM_NAME)  # Complete stream deletion
        except Exception:
            pass
        await test_redis_client.xgroup_create(self.STREAM_NAME, self.GROUP_NAME, id="0", mkstream=True)

        expired_id_1 = _create_old_event_id(seconds_in_past=4000)
        expired_id_2 = _create_old_event_id(seconds_in_past=3700)
        recent_id = _create_old_event_id(seconds_in_past=300)

        payload = completion_payload_factory.build(match_id=111)
        payload_2 = completion_payload_factory.build(match_id=222)
        payload_3 = completion_payload_factory.build(match_id=333)

        current_time_iso = get_current_utc_iso_timestamp().isoformat()

        await test_redis_client.xadd(
            self.STREAM_NAME,
            {"payload": payload.model_dump_json(), "match_id": "111", "timestamp": current_time_iso},
            id=expired_id_1,
        )
        await test_redis_client.xadd(
            self.STREAM_NAME,
            {"payload": payload_2.model_dump_json(), "match_id": "222", "timestamp": current_time_iso},
            id=expired_id_2,
        )
        await test_redis_client.xadd(
            self.STREAM_NAME,
            {"payload": payload_3.model_dump_json(), "match_id": "333", "timestamp": current_time_iso},
            id=recent_id,
        )

        await test_redis_client.xreadgroup(self.GROUP_NAME, self.CONSUMER_1, {self.STREAM_NAME: ">"}, count=3)
        expired_ids_to_claim = await redis_service_test_subject.fetch_expired_events(
            stream_name=self.STREAM_NAME, consumer_group=self.GROUP_NAME, duration=3600
        )
        assert set(expired_ids_to_claim) == {expired_id_1, expired_id_2}

        claimed_and_parsed_events = await redis_service_test_subject.claim_expired_events(
            events_id_list=expired_ids_to_claim,
            stream_name=self.STREAM_NAME,
            consumer_group=self.GROUP_NAME,
            consumer_name=self.JANITOR_CONSUMER,
            payload_model=CompletionPayload,
        )

        assert len(claimed_and_parsed_events) == 2
        claimed_match_ids = {event.match_id for event in claimed_and_parsed_events}
        assert claimed_match_ids == {111, 222}

        for event in claimed_and_parsed_events:
            assert isinstance(event, ConsumedEvent)
            assert isinstance(event.payload, CompletionPayload)
            assert event.event_id in [expired_id_1, expired_id_2]

        # Verify that the messages are now owned by the janitor by checking all pending messages
        all_pending = await test_redis_client.xpending_range(
            self.STREAM_NAME, self.GROUP_NAME, min="-", max="+", count=10
        )

        # Separate messages by consumer
        janitor_pending_ids = {msg["message_id"] for msg in all_pending if msg["consumer"] == self.JANITOR_CONSUMER}
        original_consumer_pending_ids = {msg["message_id"] for msg in all_pending if msg["consumer"] == self.CONSUMER_1}

        assert janitor_pending_ids == {expired_id_1, expired_id_2}
        assert original_consumer_pending_ids == {recent_id}
