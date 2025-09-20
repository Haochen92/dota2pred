from collections import deque
from typing import Deque, Dict, List, Tuple

from dota_oracle_common.models.match.table import MatchTable
from dota_oracle_common.models.features.table import TeamFeaturesTable


def generate_team_features(
    all_matches: List[MatchTable],
    history_limit: int = 20,
) -> List[TeamFeaturesTable]:
    """Generate causally-correct team features for a list of matches.

    Defensive sorting guarantees no data leakage even if the input list is unsorted.

    Args:
            all_matches: List of MatchTable rows. Order doesn't matter.
            history_limit: Rolling window size for win-rate histories.

    Returns:
            List of TeamFeaturesTable rows in chronological order.
    """
    if not all_matches:
        return []

    # DEFENSIVE SORT to ensure causal correctness
    sorted_matches = sorted(all_matches, key=lambda m: m.start_time)

    # Histories keyed by stable team identifiers (team_id, not team names)
    team_histories: Dict[int, Deque[bool]] = {}
    matchup_histories: Dict[Tuple[int, int], Deque[bool]] = {}

    features: List[TeamFeaturesTable] = []

    for match in sorted_matches:
        radiant_id = match.radiant_team_id
        dire_id = match.dire_team_id

        # 1) CALCULATE features from history BEFORE this match
        r_hist = team_histories.get(radiant_id)
        d_hist = team_histories.get(dire_id)

        radiant_wr = (sum(r_hist) / len(r_hist)) if r_hist else 0.5
        dire_wr = (sum(d_hist) / len(d_hist)) if d_hist else 0.5

        t1, t2 = (radiant_id, dire_id) if radiant_id < dire_id else (dire_id, radiant_id)
        md_hist = matchup_histories.get((t1, t2))
        if md_hist and len(md_hist) > 0:
            t1_wins = sum(md_hist)
            total = len(md_hist)
            # matchup is expressed as radiant vs dire
            matchup_wr = (t1_wins / total) if radiant_id == t1 else ((total - t1_wins) / total)
        else:
            matchup_wr = 0.5

        # 2) CREATE feature row for this match
        features.append(
            TeamFeaturesTable(
                match_id=match.match_id,
                radiant_win_rate=radiant_wr,
                dire_win_rate=dire_wr,
                radiant_dire_matchup=matchup_wr,
            )
        )

        # 3) UPDATE histories with the OUTCOME of this match (if present)
        outcome = getattr(match, "outcome", None)
        if outcome is not None and getattr(outcome, "radiant_win", None) is not None:
            radiant_won = bool(outcome.radiant_win)
            team_histories.setdefault(radiant_id, deque(maxlen=history_limit)).append(radiant_won)
            team_histories.setdefault(dire_id, deque(maxlen=history_limit)).append(not radiant_won)

            t1_won = radiant_won if radiant_id == t1 else (not radiant_won)
            matchup_histories.setdefault((t1, t2), deque(maxlen=history_limit)).append(t1_won)

    return features
