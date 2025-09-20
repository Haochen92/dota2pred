from collections import deque
from typing import Deque, Dict, List, Tuple

from dota_oracle_common.models.match.table import MatchTable
from dota_oracle_common.models.features.table import PlayerHeroFeatureTable


PLAYER_SLOTS: Tuple[int, ...] = (0, 1, 2, 3, 4, 128, 129, 130, 131, 132)


def generate_player_hero_features(
    all_matches: List[MatchTable],
    history_limit: int = 20,
) -> List[PlayerHeroFeatureTable]:
    """Generate causally-correct player-hero features for a list of matches.

    Defensive sorting guarantees no data leakage even if the input list is unsorted.

    Args:
            all_matches: List of MatchTable rows. Order doesn't matter.
            history_limit: Rolling window size for player-hero win-rate histories.

    Returns:
            List of PlayerHeroFeatureTable rows in chronological order.
    """
    if not all_matches:
        return []

    # DEFENSIVE SORT to ensure causal correctness
    sorted_matches = sorted(all_matches, key=lambda m: m.start_time)

    # Histories keyed by (account_id, hero_id)
    ph_histories: Dict[Tuple[int, int], Deque[bool]] = {}

    features: List[PlayerHeroFeatureTable] = []

    for match in sorted_matches:
        # 1) CALCULATE features from history BEFORE this match
        fields: Dict[str, float] = {}

        for slot in PLAYER_SLOTS:
            account_id: int = getattr(match, f"slot_{slot}_account_id")
            hero_id: int = getattr(match, f"slot_{slot}_hero_id")
            hist_key = (account_id, hero_id)
            hist = ph_histories.get(hist_key)
            win_rate = (sum(hist) / len(hist)) if hist else 0.5
            fields[f"player_hero_{slot}_win_rate"] = float(win_rate)

        # 2) CREATE feature row for this match (all required fields populated)
        features.append(
            PlayerHeroFeatureTable(
                match_id=match.match_id,
                player_hero_0_win_rate=fields["player_hero_0_win_rate"],
                player_hero_1_win_rate=fields["player_hero_1_win_rate"],
                player_hero_2_win_rate=fields["player_hero_2_win_rate"],
                player_hero_3_win_rate=fields["player_hero_3_win_rate"],
                player_hero_4_win_rate=fields["player_hero_4_win_rate"],
                player_hero_128_win_rate=fields["player_hero_128_win_rate"],
                player_hero_129_win_rate=fields["player_hero_129_win_rate"],
                player_hero_130_win_rate=fields["player_hero_130_win_rate"],
                player_hero_131_win_rate=fields["player_hero_131_win_rate"],
                player_hero_132_win_rate=fields["player_hero_132_win_rate"],
            )
        )

        # 3) UPDATE histories with the OUTCOME of this match (if present)
        outcome = getattr(match, "outcome", None)
        if outcome is not None and getattr(outcome, "radiant_win", None) is not None:
            radiant_won = bool(outcome.radiant_win)
            # Radiant slots 0-4; Dire slots 128-132
            for slot in PLAYER_SLOTS:
                account_id: int = getattr(match, f"slot_{slot}_account_id")
                hero_id: int = getattr(match, f"slot_{slot}_hero_id")
                hist_key = (account_id, hero_id)
                player_won = radiant_won if slot < 100 else (not radiant_won)
                ph_histories.setdefault(hist_key, deque(maxlen=history_limit)).append(player_won)

    return features
