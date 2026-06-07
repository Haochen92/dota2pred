DRAFT_COLS = [
    "slot_0_hero_id",
    "slot_1_hero_id",
    "slot_2_hero_id",
    "slot_3_hero_id",
    "slot_4_hero_id",
    "slot_128_hero_id",
    "slot_129_hero_id",
    "slot_130_hero_id",
    "slot_131_hero_id",
    "slot_132_hero_id",
]
PLAYER_COLS = [
    "slot_0_account_id",
    "slot_1_account_id",
    "slot_2_account_id",
    "slot_3_account_id",
    "slot_4_account_id",
    "slot_128_account_id",
    "slot_129_account_id",
    "slot_130_account_id",
    "slot_131_account_id",
    "slot_132_account_id",
]
TEAM_COL = ["radiant_name", "dire_name"]
LABEL_COL = "radiant_win"
TIME_COL = "start_time"
UUID_COL = "match_id"

# The completion pipeline resolves a finished match via the FREE /proMatches feed for this
# long; after it, the match is handed to the paid per-match StaleMatchService. Both the fresh
# (free) lookup cutoff and the stale takeover point use this single value so they can't drift
# apart and leave a coverage gap.
COMPLETION_FREE_FEED_WINDOW_SECONDS = 7200  # 2h
