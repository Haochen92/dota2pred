from collections import Counter
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List

import pandas as pd

from dota_oracle_common.models.match.table import MatchTable


# Team slot definitions
RADIANT_SLOTS: Tuple[int, ...] = (0, 1, 2, 3, 4)
DIRE_SLOTS: Tuple[int, ...] = (128, 129, 130, 131, 132)
PLAYER_SLOTS: Tuple[int, ...] = RADIANT_SLOTS + DIRE_SLOTS


@dataclass
class PlayerHeroDecayState:
    """Tracks exponentially decayed wins/games and last update for an entity.

    Attributes:
        weighted_wins: Decayed count of wins.
        weighted_games: Decayed count of games.
        last_timestamp: Unix timestamp (seconds) of last update.
    """
    weighted_wins: float = 0.0
    weighted_games: float = 0.0
    last_timestamp: int = 0


def default_winrate(alpha: int, beta: int) -> float:
    """Returns the static prior win rate alpha/beta."""
    return alpha / beta


def sorted_by_start_time(all_matches: List[MatchTable]) -> List[MatchTable]:
    """Sorts matches by ascending start_time for causal processing."""
    return sorted(all_matches, key=lambda m: m.start_time)


def get_player_hero_key(
    match: MatchTable, slot: int
) -> Tuple[Optional[int], Optional[int]]:
    """Extracts (account_id, hero_id) for a given `slot` from `match`."""
    account_id = getattr(match, f"slot_{slot}_account_id", None)
    hero_id = getattr(match, f"slot_{slot}_hero_id", None)
    return account_id, hero_id


def get_radiant_won(match: MatchTable) -> Optional[bool]:
    """Returns True/False for radiant win if available, else None."""
    outcome = getattr(match, "outcome", None)
    if outcome and hasattr(outcome, "radiant_win"):
        return outcome.radiant_win
    return None


def ts(dt) -> int:
    """Converts a datetime-like to Unix seconds."""
    return int(dt.timestamp())


def apply_decay_to_pair(
    w_wins: float, w_games: float, last_ts: int, now_ts: int, half_life_days: float
) -> Tuple[float, float]:
    """Applies exponential decay to a (wins, games) pair between timestamps."""
    if now_ts <= last_ts:
        return w_wins, w_games
    if half_life_days <= 0:
        return w_wins, w_games

    delta_seconds = now_ts - last_ts
    factor = 0.5 ** (delta_seconds / (half_life_days * 86400.0))
    return w_wins * factor, w_games * factor


def read_wr_decay(
    state: Optional[PlayerHeroDecayState],
    now_ts: int,
    alpha: int,
    beta: int,
    half_life_days: float,
    default_wr: float,
) -> float:
    """Reads decayed winrate from a `PlayerHeroDecayState` with Bayesian prior."""
    if state is None:
        return default_wr
    w_wins, w_games, last_ts = state.weighted_wins, state.weighted_games, state.last_timestamp
    w_wins, w_games = apply_decay_to_pair(w_wins, w_games, last_ts, now_ts, half_life_days)
    return (w_wins + alpha) / (w_games + beta) if (w_games + beta) > 0 else default_wr


def update_state_decay(
    state: Optional[PlayerHeroDecayState],
    now_ts: int,
    player_won: bool,
    half_life_days: float,
) -> PlayerHeroDecayState:
    """Updates or initializes a `PlayerHeroDecayState` at `now_ts` with outcome."""
    if state is None:
        state = PlayerHeroDecayState(0.0, 0.0, now_ts)
    else:
        w_wins, w_games = apply_decay_to_pair(
            state.weighted_wins, state.weighted_games, state.last_timestamp, now_ts, half_life_days
        )
        state = PlayerHeroDecayState(w_wins, w_games, now_ts)

    # Add current game
    state.weighted_games += 1.0
    if player_won:
        state.weighted_wins += 1.0
    return state


def read_wr_decay_dynamic(
    state: Optional[PlayerHeroDecayState],
    now_ts: int,
    credibility_C: int,
    half_life_days: float,
    prior_rate: float,
) -> float:
    """Reads decayed winrate blended with a credibility-weighted prior rate."""
    if state is None:
        return prior_rate
    w_wins, w_games, last_ts = state.weighted_wins, state.weighted_games, state.last_timestamp
    w_wins, w_games = apply_decay_to_pair(w_wins, w_games, last_ts, now_ts, half_life_days)
    numerator = w_wins + (credibility_C * prior_rate)
    denominator = w_games + credibility_C
    return numerator / denominator if denominator > 0 else prior_rate


def analyze_pair_counts(all_matches: List[MatchTable]) -> pd.DataFrame:
    """Summarizes how often unique (player, hero) pairs occur across matches."""
    if not all_matches:
        return pd.DataFrame(
            columns=["play_count", "num_pairs", "cumulative_pairs", "cumulative_pct"]
        )

    print(f"Analyzing counts for {len(all_matches)} matches...")

    pair_counts = Counter()
    for match in all_matches:
        for slot in PLAYER_SLOTS:
            key = get_player_hero_key(match, slot)
            if key[0] is not None and key[1] is not None:
                pair_counts[key] += 1

    if not pair_counts:
        return pd.DataFrame(
            columns=["play_count", "num_pairs", "cumulative_pairs", "cumulative_pct"]
        )

    count_distribution = Counter(pair_counts.values())

    df = (
        pd.DataFrame(count_distribution.items(), columns=["play_count", "num_pairs"]) 
        .sort_values("play_count")
        .reset_index(drop=True)
    )

    total_unique_pairs = df["num_pairs"].sum()
    df["cumulative_pairs"] = df["num_pairs"].cumsum()
    df["cumulative_pct"] = (df["cumulative_pairs"] / total_unique_pairs * 100).round(2)

    print("Analysis complete.")
    return df
