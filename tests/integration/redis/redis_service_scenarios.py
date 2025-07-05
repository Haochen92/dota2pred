from dota_oracle_common.models.redis.schema import MatchProcessingStatus
from dota_oracle_common.constants.redis_constants import (
    STREAM_NEW_MATCHES,
    STREAM_PENDING_PREDICTION,
    STREAM_PENDING_COMPLETION,
    FEATURE_ENGINEER_GROUP,
    PREDICTION_GROUP,
    COMPLETION_GROUP,
)


# Scenarios for update_live
UPDATE_LIVE_MATCH_SCENARIOS_ARGS = [
    "test_id",
    "initial_redis_match_set",
    "input_current_ids",
    "expected_new_ids_returned",
    "expected_final_redis_match_set",
]

UPDATE_LIVE_MATCH_SCENARIOS = [
    ("blank_state_all_new", set(), [1, 2, 3], {1, 2, 3}, {1, 2, 3}),
    ("existing_data_some_new_overlap", {1, 2, 3}, [2, 4, 5], {4, 5}, {2, 4, 5}),
    ("existing_data_all_overlap_no_new", {1, 2, 3}, [1, 2, 3], set(), {1, 2, 3}),
]

# Scenarios for adding new matches

ADD_NEW_MATCH_SCENARIOS_ARGS = ["test_id", "input_match_id", "expected_match_status", "expected_return_value"]
ADD_NEW_MATCH_SCENARIOS = [
    ("happy path", 12, "new", True),  # test_id  # input_match_id  # expected match status  # expected return value
    ("empty input", None, None, False),
    ("input of wrong format", "123", None, False),
]

# Scenarios for advance to next stage

ADVANCE_MATCH_TO_NEXT_ARG_NAMES = [
    "test_id",
    "method_to_call",
    "from_stream",
    "to_stream",
    "from_consumer_group",
    "expected_match_status",
    "test_match_id",
    "prev_event_match_id",  # Changed from prev_event_dict to just match_id data
    "expected_return_val",
]

ADVANCE_MATCH_TO_NEXT_SCENARIOS = [
    (
        "test_happy_path_from_fe_to_complete",
        "advance_match_to_pending_prediction",
        STREAM_NEW_MATCHES,
        STREAM_PENDING_PREDICTION,
        FEATURE_ENGINEER_GROUP,
        MatchProcessingStatus.PENDING_PREDICTION,
        123,
        123,  # match_id for building StreamMatchEventData
        True,
    ),
    (
        "test_invalid_data_from_fe_to_complete",
        "advance_match_to_pending_prediction",
        STREAM_NEW_MATCHES,
        STREAM_PENDING_PREDICTION,
        FEATURE_ENGINEER_GROUP,
        None,
        "123abc",
        123,  # match_id for building StreamMatchEventData
        False,
    ),
    (
        "test_happy_path_from_predict_to_complete",
        "advance_match_to_pending_completion",
        STREAM_PENDING_PREDICTION,
        STREAM_PENDING_COMPLETION,
        PREDICTION_GROUP,
        MatchProcessingStatus.PENDING_COMPLETION,
        754,
        754,  # match_id for building StreamMatchEventData
        True,
    ),
    (
        "test_invalid_data_from_predict_to_complete",
        "advance_match_to_pending_completion",
        STREAM_PENDING_PREDICTION,
        STREAM_PENDING_COMPLETION,
        PREDICTION_GROUP,
        None,
        "table123",
        754,  # match_id for building StreamMatchEventData
        False,
    ),
]

# Scenario for fetch events
FETCH_MATCHES_SCENARIOS_ARGS = [
    "test_id",
    "method_to_call",
    "stream_to_fetch_from",
    "consumer_group",
    "input_match_ids",  # Changed from input_list to just match_ids
    "consumer_name",
    "fetch_count",
    "expected_match_ids",
]
FETCH_MATCHES_SCENARIOS = [
    (
        "fetch_new_matches_single_event",  # test_id
        "fetch_new_matches_for_feature_eng",  # method_to_call
        STREAM_NEW_MATCHES,  # Stream_to_fetch_from
        FEATURE_ENGINEER_GROUP,  # consumer_group
        [100],  # input_match_ids to build StreamMatchEventData
        "test_consumer_fe",  # Consumer_name
        1,  # fetch_count for number of events to fetch
        {100},  # expected_match_ids set of match_ids expected back
    ),
    (
        "fetch_new_matches_multiple_events",
        "fetch_new_matches_for_feature_eng",
        STREAM_NEW_MATCHES,
        FEATURE_ENGINEER_GROUP,
        [101, 102, 103],  # input_match_ids to build StreamMatchEventData
        "test_consumer_fe",
        10,
        {101, 102, 103},
    ),
    (
        "fetch_pending_prediction_single_event",
        "fetch_matches_pending_prediction",
        STREAM_PENDING_PREDICTION,
        PREDICTION_GROUP,
        [104],  # input_match_ids to build StreamMatchEventData
        "test_consumer_pred",
        1,
        {104},
    ),
    (
        "fetch_pending_completion_no_events",
        "fetch_matches_pending_completion",
        STREAM_PENDING_COMPLETION,
        COMPLETION_GROUP,
        [],  # empty input
        "test_consumer_completion",
        10,
        set(),
    ),
]

# Scenarios for Failure Record

FAILURE_RECORD_SCENARIO_ARGS = ["test_id", "test_stream_input", "test_original_group"]

FAILURE_RECORD_SCENARIO = [
    ("happy_path", STREAM_PENDING_PREDICTION, PREDICTION_GROUP),
    ("test_failure_record_missing_target_hash", "invalid123", PREDICTION_GROUP),
]
