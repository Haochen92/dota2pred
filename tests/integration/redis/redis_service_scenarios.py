from dota_oracle_common.constants.redis_constants import (
    STREAM_NEW_MATCHES,
    STREAM_PENDING_PREDICTION,
    STREAM_PENDING_COMPLETION,
    FEATURE_ENGINEER_GROUP,
    PREDICTION_GROUP,
    COMPLETION_GROUP,
)
from dota_oracle_common.models.redis.schema import (
    FeatureEngineeringPayload,
    PredictionPayload,
    CompletionPayload,
)

# Scenarios for update_live_match_set_and_get_new
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

# Scenarios for publish_new_match_to_feature_eng
PUBLISH_NEW_MATCH_SCENARIOS_ARGS = ["test_id", "match_id", "expected_return_value"]
PUBLISH_NEW_MATCH_SCENARIOS = [
    ("happy_path", 12345, True),
    # Failure cases are hard to trigger here without a mock redis client,
    # so we focus on the successful path.
]


# Scenarios for advancing from Feature Engineering to Prediction
PUBLISH_FEATURES_SCENARIOS_ARGS = ["test_id", "match_id", "expected_return_val"]
PUBLISH_FEATURES_SCENARIOS = [
    ("happy_path", 123, True),
]

# Scenarios for advancing from Prediction to Completion
PUBLISH_PREDICTION_SCENARIOS_ARGS = ["test_id", "match_id", "expected_return_val"]
PUBLISH_PREDICTION_SCENARIOS = [
    ("happy_path", 789, True),
]

# Scenarios for fetch events
FETCH_MATCHES_SCENARIOS_ARGS = [
    "test_id",
    "method_to_call",
    "stream_to_fetch_from",
    "consumer_group",
    "payload_type_to_seed",
    "expected_payload_type",
    "input_match_ids",
    "consumer_name",
    "fetch_count",
    "expected_match_ids",
]
FETCH_MATCHES_SCENARIOS = [
    (
        "fetch_new_matches_single_event",
        "fetch_new_matches_for_feature_eng",
        STREAM_NEW_MATCHES,
        FEATURE_ENGINEER_GROUP,
        FeatureEngineeringPayload,
        FeatureEngineeringPayload,
        [100],
        "test_consumer_fe",
        1,
        {100},
    ),
    (
        "fetch_new_matches_multiple_events",
        "fetch_new_matches_for_feature_eng",
        STREAM_NEW_MATCHES,
        FEATURE_ENGINEER_GROUP,
        FeatureEngineeringPayload,
        FeatureEngineeringPayload,
        [101, 102, 103],
        "test_consumer_fe",
        10,
        {101, 102, 103},
    ),
    (
        "fetch_prediction_matches_single_event",
        "fetch_matches_for_prediction",
        STREAM_PENDING_PREDICTION,
        PREDICTION_GROUP,
        PredictionPayload,
        PredictionPayload,
        [104],
        "test_consumer_pred",
        1,
        {104},
    ),
    (
        "fetch_completion_matches_no_events",
        "fetch_matches_for_completion",
        STREAM_PENDING_COMPLETION,
        COMPLETION_GROUP,
        CompletionPayload,
        CompletionPayload,
        [],
        "test_consumer_completion",
        10,
        set(),
    ),
]

# Scenarios for Failure Record

FAILURE_RECORD_SCENARIO_ARGS = ["test_id", "test_stream_input", "test_original_group"]

FAILURE_RECORD_SCENARIO = [
    ("happy_path_prediction_stream", STREAM_PENDING_PREDICTION, PREDICTION_GROUP),
    ("happy_path_completion_stream", STREAM_PENDING_COMPLETION, COMPLETION_GROUP),
    ("test_failure_record_unknown_stream", "invalid-stream-123", "unknown-group"),
]
