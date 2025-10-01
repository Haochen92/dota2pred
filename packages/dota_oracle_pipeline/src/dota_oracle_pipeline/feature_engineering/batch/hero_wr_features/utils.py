from collections import Counter
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from dota_oracle_common.models.match.table import MatchTable


RADIANT_SLOTS: Tuple[int, ...] = (0, 1, 2, 3, 4)
DIRE_SLOTS: Tuple[int, ...] = (128, 129, 130, 131, 132)


def default_winrate(alpha: int, beta: int) -> float:
    return alpha / beta


def sorted_by_start_time(all_matches: List[MatchTable]) -> List[MatchTable]:
    return sorted(all_matches, key=lambda m: m.start_time)


def ts(sec_or_dt) -> int:
    try:
        return int(sec_or_dt.timestamp())
    except AttributeError:
        return int(sec_or_dt)


def get_radiant_won(match: MatchTable) -> Optional[bool]:
    outcome = getattr(match, "outcome", None)
    if outcome is None:
        return None
    if getattr(outcome, "radiant_win", None) is None:
        return None
    return bool(outcome.radiant_win)


def extract_hero_picks(match: MatchTable) -> Tuple[List[int], List[int]]:
    radiant = [getattr(match, f"slot_{s}_hero_id") for s in RADIANT_SLOTS]
    dire = [getattr(match, f"slot_{s}_hero_id") for s in DIRE_SLOTS]
    return radiant, dire


def extract_hero_picks_optional(match: MatchTable) -> Tuple[List[Optional[int]], List[Optional[int]]]:
    radiant = [getattr(match, f"slot_{s}_hero_id", None) for s in RADIANT_SLOTS]
    dire = [getattr(match, f"slot_{s}_hero_id", None) for s in DIRE_SLOTS]
    return radiant, dire


def apply_decay_to_pair(wins_w: float, games_w: float, last_ts: int, now_ts: int, half_life_days: float) -> Tuple[float, float]:
    if now_ts <= last_ts:
        return wins_w, games_w
    if half_life_days <= 0:
        return wins_w, games_w
    delta_seconds = now_ts - last_ts
    factor = 0.5 ** (delta_seconds / (half_life_days * 86400.0))
    return wins_w * factor, games_w * factor


def build_agg_row(
    match_id: int, radiant_wrs: List[float], dire_wrs: List[float], default_wr: float
) -> Dict[str, float]:
    r_avg = float(np.mean(radiant_wrs)) if radiant_wrs else default_wr
    d_avg = float(np.mean(dire_wrs)) if dire_wrs else default_wr
    r_max = float(np.max(radiant_wrs)) if radiant_wrs else default_wr
    d_max = float(np.max(dire_wrs)) if dire_wrs else default_wr
    return dict(
        match_id=match_id,
        radiant_avg_hero_winrate=r_avg,
        dire_avg_hero_winrate=d_avg,
        radiant_max_hero_winrate=r_max,
        dire_max_hero_winrate=d_max,
    )


def analyze_hero_counts(all_matches: List[MatchTable]) -> pd.DataFrame:
    if not all_matches:
        return pd.DataFrame()

    print(f"Analyzing hero pick counts for {len(all_matches)} matches...")
    hero_counts = Counter()
    for match in all_matches:
        radiant_picks, dire_picks = extract_hero_picks_optional(match)
        for hero_id in radiant_picks + dire_picks:
            if hero_id is not None:
                hero_counts[hero_id] += 1

    if not hero_counts:
        return pd.DataFrame()

    count_distribution = Counter(hero_counts.values())
    df = (
        pd.DataFrame(count_distribution.items(), columns=["play_count", "num_heroes"]) 
        .sort_values("play_count")
        .reset_index(drop=True)
    )

    total_unique_heroes = df["num_heroes"].sum()
    df["cumulative_heroes"] = df["num_heroes"].cumsum()
    df["cumulative_pct"] = (df["cumulative_heroes"] / total_unique_heroes * 100).round(2)

    print("Analysis complete.")
    return df

