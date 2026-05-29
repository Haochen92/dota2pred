MATCH_SET = "live_match_ids"
MATCH_STATUS = "match_status"

# Streams
STREAM_NEW_MATCHES = "new_matches"
STREAM_PENDING_PREDICTION = "pending_prediction"
STREAM_PENDING_COMPLETION = "pending_completion"

# Group
FEATURE_ENGINEER_GROUP = "feature_engineer_group"
PREDICTION_GROUP = "prediction_group"
COMPLETION_GROUP = "completion_group"

TMP_KEY = f"{MATCH_SET}:temp"

# Failed events hashes
FAILED_EVENTS_HASH_NEW = "failed_events:new_matches"
FAILED_EVENTS_HASH_PENDING_PREDICTION = "failed_events:pending_prediction"
FAILED_EVENTS_HASH_PENDING_COMPLETION = "failed_events:pending_completion"

# Failed Stream hash mapping
FAILED_EVENTS_MAPPING = {
    STREAM_NEW_MATCHES: FAILED_EVENTS_HASH_NEW,
    STREAM_PENDING_PREDICTION: FAILED_EVENTS_HASH_PENDING_PREDICTION,
    STREAM_PENDING_COMPLETION: FAILED_EVENTS_HASH_PENDING_COMPLETION,
}

# DLQ retry tracking
DLQ_RETRY_COUNTS_HASH = "dlq:retry_counts"
