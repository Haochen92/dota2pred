import pytest

from redis.asyncio import Redis as AIORedis
from typing import Any, Set, List, Dict
import json


from dota_oracle_common.models.redis.schema import StreamMatchEventData, FailureRecord
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

from live_orchestrator_app.services.redis_service import RedisService

from .redis_service_scenarios import (
    UPDATE_LIVE_MATCH_SCENARIOS_ARGS,
    UPDATE_LIVE_MATCH_SCENARIOS,
    ADD_NEW_MATCH_SCENARIOS_ARGS,
    ADD_NEW_MATCH_SCENARIOS,
    ADVANCE_MATCH_TO_NEXT_ARG_NAMES,
    ADVANCE_MATCH_TO_NEXT_SCENARIOS,
    FETCH_MATCHES_SCENARIOS_ARGS,
    FETCH_MATCHES_SCENARIOS,
    FAILURE_RECORD_SCENARIO_ARGS,
    FAILURE_RECORD_SCENARIO,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

"""
Test Service initialization
"""


async def test_initialize_redis_service(redis_service_test_subject: RedisService, test_redis_client: AIORedis) -> None:
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

        # You could also check 'mkstream=True' behavior by ensuring streams exist
        assert await test_redis_client.exists(stream_name), f"Stream '{stream_name}' was not created."

    # Verify idempotency (calling initialize again should not fail)
    await redis_service_test_subject.initialize_async_service()
    # Re-check one group to be sure
    groups_info = await test_redis_client.xinfo_groups(STREAM_NEW_MATCHES)
    assert any(
        group_info["name"] == FEATURE_ENGINEER_GROUP for group_info in groups_info
    ), "Consumer group disappeared after second initialize call."


"""
Testing New Match orchestration related operations
"""


@pytest.mark.parametrize(UPDATE_LIVE_MATCH_SCENARIOS_ARGS, UPDATE_LIVE_MATCH_SCENARIOS)
async def test_update_live_match(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    test_id: str,
    initial_redis_match_set: set[int],
    input_current_ids: list[int],
    expected_new_ids_returned: set[int],
    expected_final_redis_match_set: set[int],
) -> None:
    """Setting up the initial environment"""
    # clean up match_set and temp_key to ensure clean state
    await test_redis_client.delete(MATCH_SET, TMP_KEY)
    if initial_redis_match_set:
        await test_redis_client.sadd(MATCH_SET, *[str(id_val) for id_val in initial_redis_match_set])  # type: ignore

    returned_new_ids = await redis_service_test_subject.update_live_match_set_and_get_new(input_current_ids)
    assert (
        returned_new_ids == expected_new_ids_returned
    ), f"Test ID '{test_id}': Incorrect Return value from RedisService"

    actual_final_redis_match_set_str = await test_redis_client.smembers(MATCH_SET)  # type:ignore
    actual_final_redis_match_set = {int(val) for val in actual_final_redis_match_set_str}

    assert (
        actual_final_redis_match_set == expected_final_redis_match_set
    ), f"Test ID '{test_id}': Incorrect final state of MATCH_SET in Redis."


"""
Test adding new matches
"""


@pytest.mark.parametrize(ADD_NEW_MATCH_SCENARIOS_ARGS, ADD_NEW_MATCH_SCENARIOS)
async def test_add_new_match(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    test_id: str,
    input_match_id: Any,
    expected_match_status: str | None,
    expected_return_value: bool,
) -> None:
    match_status_key = f"{MATCH_STATUS}:{input_match_id}"
    # clean up
    await test_redis_client.delete(match_status_key)
    await test_redis_client.xtrim(STREAM_NEW_MATCHES, maxlen=0)

    actual_return_value = await redis_service_test_subject.add_match_for_processing(input_match_id)
    assert (
        actual_return_value == expected_return_value
    ), f"got {actual_return_value} expected {expected_return_value} for test {test_id}"

    if expected_return_value is True:
        actual_match_status = await test_redis_client.hget(match_status_key, "status")  # type: ignore
        assert (
            actual_match_status == expected_match_status
        ), f"got {actual_match_status} expected {expected_match_status} for test {test_id}"

        # test for actual data in stream
        stream_entries = await test_redis_client.xrevrange(STREAM_NEW_MATCHES, count=1)
        assert len(stream_entries) > 0, f"Test ID '{test_id}': No entry found in stream after successful add"

        latest_event_id, latest_event_data = stream_entries[0]
        assert (
            latest_event_data is not None
        ), f"Test Id '{test_id}: Latest event data in stream {STREAM_NEW_MATCHES} is None"

        assert (
            int(latest_event_data.get("match_id")) == input_match_id
        ), f"Test ID '{test_id}': match_id in stream incorrect. Expected {input_match_id} got {latest_event_data.get('match_id')}"

        assert "timestamp" in latest_event_data, f"Test ID '{test_id}': Timestamp missing from stream event data."

    else:
        assert not await test_redis_client.exists(
            match_status_key
        ), f"Test ID '{test_id}': Match status key '{match_status_key}' should not exist for failed operation."

        stream_entries_after_fail = await test_redis_client.xrevrange(STREAM_NEW_MATCHES, count=1)
        assert (
            len(stream_entries_after_fail) == 0
        ), f"Test ID '{test_id}': Stream '{STREAM_NEW_MATCHES}' should be empty after failed operation due to invalid input."


"""
Test advancing match to next stage
"""


@pytest.mark.parametrize(
    ADVANCE_MATCH_TO_NEXT_ARG_NAMES,
    ADVANCE_MATCH_TO_NEXT_SCENARIOS,
)
async def test_advance_match_to_next(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    stream_match_event_data_factory,
    test_id: str,
    method_to_call: str,
    from_stream: str,
    to_stream: str,
    from_consumer_group: str,
    expected_match_status: str,
    test_match_id: Any,
    prev_event_match_id: int,  # Changed from prev_event_dict
    expected_return_val: bool,
) -> None:
    match_status_key = f"{MATCH_STATUS}:{test_match_id}"
    # reset redis status
    await test_redis_client.delete(match_status_key)
    await test_redis_client.xtrim(from_stream, maxlen=0)
    await test_redis_client.xtrim(to_stream, maxlen=0)

    # Build event data using fixture
    prev_event_data = stream_match_event_data_factory.build(match_id=prev_event_match_id)
    prev_event_dict = prev_event_data.model_dump()

    # seeding inputs:
    await test_redis_client.xadd(from_stream, prev_event_dict)  # type:ignore
    seeded_entries = await test_redis_client.xrevrange(from_stream, count=1)
    assert len(seeded_entries) > 0, f"Test ID '{test_id}': Seeding of data failed"

    from_event_id, from_event_data = seeded_entries[0]
    assert (
        from_event_data is not None
    ), f"Test Id '{test_id}: Latest event data in stream {from_stream} is None after seeding"
    assert from_event_id is not None, f"Test Id {test_id}: event_id {from_event_id} is missing from seeded stream"

    # run test method
    actual_return_val = await getattr(redis_service_test_subject, method_to_call)(
        match_id=test_match_id, event_id_to_ack=from_event_id
    )

    # test return value
    assert (
        actual_return_val == expected_return_val
    ), f"Test_id {test_id}: expected {expected_return_val} got {actual_return_val}"

    actual_match_status = await test_redis_client.hget(match_status_key, "status")  # type: ignore
    assert (
        actual_match_status == expected_match_status
    ), f"got {actual_match_status} expected {expected_match_status} for test {test_id}"

    if actual_return_val:
        # test for actual data in stream
        stream_entries = await test_redis_client.xrevrange(to_stream, count=1)
        assert len(stream_entries) == 1, f"Test ID '{test_id}': expected 1 entry but got {len(stream_entries)}"

        latest_event_id, latest_event_data = stream_entries[0]
        assert (
            latest_event_data is not None
        ), f"Test Id '{test_id}: Latest event data in stream {from_stream} is missing"

        # test for data value
        assert (
            int(latest_event_data.get("match_id")) == test_match_id
        ), f"Test ID '{test_id}': match_id in stream incorrect. Expected {test_match_id} got {latest_event_data.get('match_id')}"

        assert "timestamp" in latest_event_data, f"Test ID '{test_id}': Timestamp missing from stream event data."

        # test for acknowledgement
        pending = await test_redis_client.xpending_range(
            name=from_stream, groupname=from_consumer_group, min=from_event_id, max=from_event_id, count=1
        )
        assert len(pending) == 0, f"Test {test_id}: event has not been acknowledged"
    else:
        stream_entries_to = await test_redis_client.xlen(to_stream)
        assert stream_entries_to == 0, f"Test ID '{test_id}': Event incorrectly added to {to_stream} on failure"

        # test for acknowledgement
        stream_entries_from = await test_redis_client.xrange(from_stream, from_event_id, from_event_id)
        assert len(stream_entries_from) == 1, f"Test {test_id}: message still exists in stream and no ACK was attempted"


"""
Test Fetch Events
"""


@pytest.mark.parametrize(FETCH_MATCHES_SCENARIOS_ARGS, FETCH_MATCHES_SCENARIOS)
async def test_fetch_events(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    stream_match_event_data_factory,
    test_id: str,
    method_to_call: str,
    stream_to_fetch_from: str,
    consumer_group: str,
    input_match_ids: List[int],  # Changed from input_list
    consumer_name: str,
    fetch_count: int,
    expected_match_ids: Set[int],
) -> None:
    # clear state and add inputs
    await test_redis_client.xtrim(stream_to_fetch_from, maxlen=0)
    if input_match_ids:
        for match_id in input_match_ids:
            # Build event data using fixture
            event_data = stream_match_event_data_factory.build(match_id=match_id)
            event_data_dict = event_data.model_dump()
            await test_redis_client.xadd(stream_to_fetch_from, event_data_dict)  # type: ignore

    # read events
    fetched_events: Dict[str, StreamMatchEventData] = await getattr(redis_service_test_subject, method_to_call)(
        consumer=consumer_name, count=fetch_count
    )

    assert len(fetched_events) == len(
        input_match_ids
    ), f"Test {test_id}: expected {len(input_match_ids)} events but got {len(fetched_events)} events"

    actual_match_ids = set()
    for event_id, data in fetched_events.items():
        actual_match_ids.add(data.match_id)

    assert (
        actual_match_ids == expected_match_ids
    ), f"Test {test_id}: expected {expected_match_ids} got {actual_match_ids} for stream {stream_to_fetch_from} consumer_group {consumer_group}"


"""
Test Failure Acknowledgement 
"""


@pytest.mark.parametrize(FAILURE_RECORD_SCENARIO_ARGS, FAILURE_RECORD_SCENARIO)
async def test_record_failure_and_ack(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    stream_match_event_data_factory,
    failure_record_factory,
    test_id: str,
    test_stream_input: str,
    test_original_group: str,
) -> None:
    # Set up
    original_stream = test_stream_input
    original_group = test_original_group
    # Build event data using fixture
    original_event_data = stream_match_event_data_factory.build(match_id=123)
    original_data = original_event_data.model_dump()
    target_dlq_hash = FAILED_EVENTS_MAPPING.get(original_stream)

    if target_dlq_hash:
        await test_redis_client.delete(target_dlq_hash)
        await test_redis_client.xtrim(original_stream, maxlen=0)
        original_event_id = await test_redis_client.xadd(original_stream, original_data, id="*")  # type: ignore

        # Build failure record using fixture
        test_failure_record = failure_record_factory.build(
            original_group=original_group,
            original_stream=original_stream,
            original_data=original_data,
            original_event_id=original_event_id,
        )

        # test return value
        actual_return_value = await redis_service_test_subject._record_failure_and_ack(test_failure_record)
        assert actual_return_value is True, f"Test ID 'test_id': Expected {True} got {actual_return_value}"

        # test target hash value
        actual_hash_dict = await test_redis_client.hgetall(target_dlq_hash)  # type:ignore

        # Check if the event_id exists as a field name and get its value
        assert (
            actual_hash_dict.get(original_event_id) is not None
        ), f"test_id {test_id}: event_id {original_event_id} not found in hash"

        expected_json = test_failure_record.model_dump_json()

        actual_data_json = actual_hash_dict.get(original_event_id)

        assert (
            actual_data_json == expected_json
        ), f"test_id {test_id}: expected data_json: {expected_json} got {actual_data_json}"

        pending = await test_redis_client.xpending_range(
            name=original_stream, groupname=original_group, min=original_event_id, max=original_event_id, count=1
        )
        assert len(pending) == 0, f"Test {test_id}: event has not been acknowledged"
    else:
        pass


async def test_record_failure_and_ack_serialization_error(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis,
    stream_match_event_data_factory,
    failure_record_factory,
    mocker,
) -> None:
    # arrange
    original_stream = STREAM_PENDING_PREDICTION
    original_group = PREDICTION_GROUP
    # Build event data using fixture
    original_event_data = stream_match_event_data_factory.build(match_id=123)
    original_data = original_event_data.model_dump()
    target_dlq_hash = FAILED_EVENTS_MAPPING[original_stream]

    # set up
    await test_redis_client.delete(target_dlq_hash)
    await test_redis_client.xtrim(original_stream, maxlen=0)
    original_event_id = await test_redis_client.xadd(original_stream, original_data, id="*")  # type: ignore

    # Build failure record using fixture
    test_failure_record = failure_record_factory.build(
        original_group=original_group,
        original_stream=original_stream,
        original_data=original_data,
        original_event_id=original_event_id,
    )

    mocked_json_dump_method = mocker.patch.object(
        FailureRecord,  # Mock class as a workaround for pydantic protection mechanism
        "model_dump_json",
        side_effect=ValueError("Simulated Serialization Error"),
        autospec=True,
    )

    # ACT
    actual_return_value = await redis_service_test_subject._record_failure_and_ack(test_failure_record)

    # Assert
    assert actual_return_value

    mocked_json_dump_method.assert_called_once()

    stored_fallback_json_str = await test_redis_client.hget(target_dlq_hash, original_event_id)  # type:ignore

    assert stored_fallback_json_str is not None, "Fallback Json not found in DLQ"
    fallback_data = json.loads(stored_fallback_json_str)

    assert fallback_data.get("error") == "DLQ data serialization failed"
    assert fallback_data.get("original_event_id") == original_event_id
    assert fallback_data.get("original_stream") == original_stream

    # Verify ACK
    pending_after_ack = await test_redis_client.xpending_range(
        name=original_stream, groupname=original_group, min=original_event_id, max=original_event_id, count=1
    )
    assert len(pending_after_ack) == 0, f"Event {original_event_id} was not ACKed on serialization error."
