import pytest
from datetime import datetime, timezone
from redis.asyncio import Redis as AIORedis
from typing import Any, Set, List, Dict

from dota_oracle.pydantic_models.redis_models import MatchProcessingStatus, MatchStatusValue, StreamMatchEventData
from dota_oracle.constants.redis_constants import (
    MATCH_SET, MATCH_STATUS, TMP_KEY,
    STREAM_NEW_MATCHES, STREAM_PENDING_PREDICTION, STREAM_PENDING_COMPLETION,
    FEATURE_ENGINEER_GROUP, PREDICTION_GROUP, COMPLETION_GROUP,
    FAILED_EVENTS_MAPPING
)

from dota_oracle.live_pipeline.redis_service import RedisService

from ..factories.redis_models_factory import StreamMatchEventDataFactory, MatchStatusValueFactory, FailureRecordFactory

pytestmark = pytest.mark.asyncio

'''
Test Service initialization
'''

async def test_initialize_redis_service(
    redis_service_test_subject: RedisService,
    test_redis_client: AIORedis
):
    await redis_service_test_subject.initialize()
    
    expected_streams_and_groups = [
        (STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP),
        (STREAM_PENDING_PREDICTION, PREDICTION_GROUP),
        (STREAM_PENDING_COMPLETION, COMPLETION_GROUP),
    ]
    
    for stream_name, group_name in expected_streams_and_groups:
        groups_info = await test_redis_client.xinfo_groups(stream_name)
        assert any(group_info['name'] == group_name for group_info in groups_info), \
            f"Consumer group '{group_name}' not found for stream '{stream_name}'"
        
        # You could also check 'mkstream=True' behavior by ensuring streams exist
        assert await test_redis_client.exists(stream_name), f"Stream '{stream_name}' was not created."

    # Verify idempotency (calling initialize again should not fail)
    await redis_service_test_subject.initialize()
    # Re-check one group to be sure
    groups_info = await test_redis_client.xinfo_groups(STREAM_NEW_MATCHES)
    assert any(group_info['name'] == FEATURE_ENGINEER_GROUP for group_info in groups_info), \
        "Consumer group disappeared after second initialize call."

'''
Testing New Match orchestration related operations
'''
# Scenarios for update_live
update_live_match_scenarios = [
    (
        "blank_state_all_new",
        set(),
        [1,2,3],
        {1,2,3},
        {1,2,3}
    ),
    (
        "existing_data_some_new_overlap",
        {1,2,3},
        [2,4,5],
        {4,5},
        {2,4,5}
    ),
    (
        "existin_data_all_overlap_no_new",
        {1,2,3},
        [1,2,3],
        set(),
        {1,2,3}
    )
]

@pytest.mark.parametrize(
    "test_id, initial_redis_match_set, input_current_ids, expected_new_ids_returned, expected_final_redis_match_set",
    update_live_match_scenarios
)
async def test_update_live_match(
    redis_service_test_subject: RedisService,
    test_redis_client:AIORedis,
    test_id: str,
    initial_redis_match_set: set[int],
    input_current_ids: list[int],
    expected_new_ids_returned: set[int],
    expected_final_redis_match_set:set[int]
):
    '''Setting up the initial environment'''
    # clean up match_set and temp_key to ensure clean state
    await test_redis_client.delete(MATCH_SET, TMP_KEY)
    if initial_redis_match_set:
        await test_redis_client.sadd(MATCH_SET, *[str(id_val) for id_val in initial_redis_match_set]) # type: ignore
    
    returned_new_ids = await redis_service_test_subject.update_live_match_set_and_get_new(input_current_ids)
    assert returned_new_ids == expected_new_ids_returned, \
        f"Test ID '{test_id}': Incorrect Return value from RedisService"
    
    actual_final_redis_match_set_str = await test_redis_client.smembers(MATCH_SET) # type:ignore
    actual_final_redis_match_set = {int(val) for val in actual_final_redis_match_set_str}
    
    assert actual_final_redis_match_set == expected_final_redis_match_set, \
        f"Test ID '{test_id}': Incorrect final state of MATCH_SET in Redis."
    

add_new_match_scenarios = [
    (
        "happy path", # test_id
        12, # input_match_id
        "new", # expected match status
        True, # expected return value
        
    ),
    (
        "empty input",
        None,
        None,
        False,
    ),
    (
        "input of wrong format",
        "123",
        None,
        False
    )
]

@pytest.mark.parametrize(
    "test_id, input_match_id, expected_match_status, expected_return_value",
    add_new_match_scenarios
)
async def test_add_new_match(
    redis_service_test_subject: RedisService,
    test_redis_client:AIORedis,
    test_id: str,
    input_match_id: Any,
    expected_match_status: str | None,
    expected_return_value: bool ,
):
    match_status_key = f"{MATCH_STATUS}:{input_match_id}"
    # clean up
    await test_redis_client.delete(match_status_key)
    await test_redis_client.xtrim(STREAM_NEW_MATCHES, maxlen=0)
    
    actual_return_value = await redis_service_test_subject.add_match_for_processing(input_match_id)
    assert actual_return_value == expected_return_value, \
        f"got {actual_return_value} expected {expected_return_value} for test {test_id}"
    
    if expected_return_value is True:
        actual_match_status = await test_redis_client.hget(match_status_key, 'status') # type: ignore
        assert actual_match_status == expected_match_status, \
            f"got {actual_match_status} expected {expected_match_status} for test {test_id}"
    

        stream_entries =await test_redis_client.xrevrange(STREAM_NEW_MATCHES, count=1)
        assert len(stream_entries) > 0, f"Test ID '{test_id}': No entry found in stream after successful add"
        
        latest_event_id, latest_event_data = stream_entries[0]
        assert latest_event_data is not None, f"Test Id '{test_id}: Latest event data in stream {STREAM_NEW_MATCHES} is None"
    
        assert int(latest_event_data.get('match_id')) == input_match_id, \
            f"Test ID '{test_id}': match_id in stream incorrect. Expected {input_match_id} got {latest_event_data.get('match_id')}"
            
        assert 'timestamp' in latest_event_data, f"Test ID '{test_id}': Timestamp missing from stream event data."
        
    else:
        assert not await test_redis_client.exists(match_status_key), \
            f"Test ID '{test_id}': Match status key '{match_status_key}' should not exist for failed operation."
        
        stream_entries_after_fail = await test_redis_client.xrevrange(STREAM_NEW_MATCHES, count=1)
        assert len(stream_entries_after_fail) == 0, \
            f"Test ID '{test_id}': Stream '{STREAM_NEW_MATCHES}' should be empty after failed operation due to invalid input."


'''
Test Fetch Events
'''

FETCH_MATCHES_SCENARIOS = [
    (
        "fetch_new_matches_single_event", # test_id
        "fetch_new_matches_for_feature_eng", # method_to_call
        STREAM_NEW_MATCHES, # Stream_to_fetch_from
        FEATURE_ENGINEER_GROUP, # consumer_group
        [StreamMatchEventDataFactory.build(match_id=100).model_dump()], # input_list of dict
        "test_consumer_fe", # Consumer_name
        1, # fetch_count for number of events to fetch
        {100} # expected_match_ids set of match_ids expected back 
    ),
    (
        "fetch_new_matches_multiple_events",
        "fetch_new_matches_for_feature_eng",
        STREAM_NEW_MATCHES,
        FEATURE_ENGINEER_GROUP,
        [
            StreamMatchEventDataFactory.build(match_id=101).model_dump(),
            StreamMatchEventDataFactory.build(match_id=102).model_dump(),
            StreamMatchEventDataFactory.build(match_id=103).model_dump()
        ],
        "test_consumer_fe",
        10,
        {101, 102, 103}
    ),
    (
        "fetch_pending_prediction_single_event",
        "fetch_matches_pending_prediction",
        STREAM_PENDING_PREDICTION,
        PREDICTION_GROUP,
        [StreamMatchEventDataFactory.build(match_id=104).model_dump()],
        "test_consumer_pred",
        1,
        {104}
    ),
    (
        "fetch_pending_completion_no_events",
        "fetch_matches_pending_completion",
        STREAM_PENDING_COMPLETION,
        COMPLETION_GROUP,
        [],
        "test_consumer_completion",
        10,
        set(),
    )
]

@pytest.mark.parametrize(
    ["test_id","method_to_call","stream_to_fetch_from",
     "consumer_group","input_list","consumer_name","fetch_count","expected_match_ids"],
    FETCH_MATCHES_SCENARIOS
)
async def test_fetch_events(
    redis_service_test_subject: RedisService,
    test_redis_client:AIORedis,
    test_id: str,
    method_to_call: str,
    stream_to_fetch_from: str,
    consumer_group: str,
    input_list: List[Dict[str,Any]],
    consumer_name: str,
    fetch_count: int,
    expected_match_ids: Set[int]
):
    # clear state and add inputs
    await test_redis_client.xtrim(stream_to_fetch_from, maxlen=0)
    if input_list:
        for event_data_dict in input_list:
            await test_redis_client.xadd(stream_to_fetch_from, event_data_dict) #type: ignore
    
    # read events
    fetched_events: Dict[str, StreamMatchEventData] = await getattr(redis_service_test_subject, method_to_call)(
        consumer=consumer_name,
        count=fetch_count
    )
    
    assert len(fetched_events) == len(input_list), \
        f"Test {test_id}: expected {len(input_list)} events but got {len(fetched_events)} events"
    
    actual_match_ids = set()
    for event_id, data in fetched_events.items():
        actual_match_ids.add(data.match_id)
        
    assert actual_match_ids == expected_match_ids, \
        f"Test {test_id}: expected {expected_match_ids} got {actual_match_ids} for stream {stream_to_fetch_from} consumer_group {consumer_group}"
    
    
    
    

