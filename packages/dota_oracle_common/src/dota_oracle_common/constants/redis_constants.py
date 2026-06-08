MATCH_SET = "live_match_ids"
MATCH_STATUS = "match_status"

# Streams
STREAM_NEW_MATCHES = "new_matches"
STREAM_PENDING_PREDICTION = "pending_prediction"
STREAM_PENDING_COMPLETION = "pending_completion"
# Odds capture is a terminal stage that branches off prediction (parallel to completion), so it
# reads its own stream rather than sharing pending_completion -- completion XDELs entries on
# settle, which would race the odds consumer if they shared a stream.
STREAM_PENDING_ODDS = "pending_odds"

# Group
FEATURE_ENGINEER_GROUP = "feature_engineer_group"
PREDICTION_GROUP = "prediction_group"
COMPLETION_GROUP = "completion_group"
ODDS_GROUP = "odds_group"

TMP_KEY = f"{MATCH_SET}:temp"

# Failed events hashes
FAILED_EVENTS_HASH_NEW = "failed_events:new_matches"
FAILED_EVENTS_HASH_PENDING_PREDICTION = "failed_events:pending_prediction"
FAILED_EVENTS_HASH_PENDING_COMPLETION = "failed_events:pending_completion"
FAILED_EVENTS_HASH_PENDING_ODDS = "failed_events:pending_odds"

# Failed Stream hash mapping
FAILED_EVENTS_MAPPING = {
    STREAM_NEW_MATCHES: FAILED_EVENTS_HASH_NEW,
    STREAM_PENDING_PREDICTION: FAILED_EVENTS_HASH_PENDING_PREDICTION,
    STREAM_PENDING_COMPLETION: FAILED_EVENTS_HASH_PENDING_COMPLETION,
    STREAM_PENDING_ODDS: FAILED_EVENTS_HASH_PENDING_ODDS,
}

# DLQ retry tracking
DLQ_RETRY_COUNTS_HASH = "dlq:retry_counts"
