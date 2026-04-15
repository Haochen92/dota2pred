from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from dota_oracle_common.models.features.table import TeamFeaturesTable
from dota_oracle_common.models.match.table import MatchTable

from .utils import (
    default_winrate,
    get_matchup_key,
    get_matchup_key_and_outcome,
    get_radiant_won,
    sorted_by_start_time,
)


class TeamWindowFeatureGenerator:
    """Generate team and matchup win rate features using rolling windows."""

    def generate(
        self,
        all_matches: List[MatchTable],
        *,
        alpha: int = 1,
        beta: int = 2,
        window_size: int = 20,
    ) -> List[TeamFeaturesTable]:
        assert window_size > 0, "window_size must be a positive integer."
        if not all_matches:
            return []

        matches = sorted_by_start_time(all_matches)
        default_wr = default_winrate(alpha, beta)

        team_histories: Dict[int, Deque[bool]] = {}
        matchup_histories: Dict[Tuple[int, int], Deque[bool]] = {}

        feature_rows: List[TeamFeaturesTable] = []
        for match in matches:
            rad_id, dire_id = match.radiant_team_id, match.dire_team_id

            radiant_wr = self._read_wr_window(team_histories.get(rad_id), alpha, beta)
            dire_wr = self._read_wr_window(team_histories.get(dire_id), alpha, beta)
            matchup_wr = self._read_matchup_wr_window(matchup_histories, rad_id, dire_id, alpha, beta)

            feature_rows.append(
                TeamFeaturesTable(
                    match_id=match.match_id,
                    radiant_win_rate=radiant_wr or default_wr,
                    dire_win_rate=dire_wr or default_wr,
                    radiant_dire_matchup=matchup_wr or default_wr,
                )
            )

            radiant_won = get_radiant_won(match)
            if radiant_won is not None:
                team_histories.setdefault(rad_id, deque(maxlen=window_size)).append(radiant_won)
                team_histories.setdefault(dire_id, deque(maxlen=window_size)).append(not radiant_won)

                key, t1_won = get_matchup_key_and_outcome(rad_id, dire_id, radiant_won)
                matchup_histories.setdefault(key, deque(maxlen=window_size)).append(t1_won)

        return feature_rows

    # helpers
    def _read_wr_window(self, history: Optional[Deque[bool]], alpha: int, beta: int) -> Optional[float]:
        if not history:
            return None
        return (sum(history) + alpha) / (len(history) + beta)

    def _read_matchup_wr_window(
        self, histories: Dict[Tuple[int, int], Deque[bool]], rad_id: int, dire_id: int, alpha: int, beta: int
    ) -> Optional[float]:
        key = get_matchup_key(rad_id, dire_id)
        history = histories.get(key)
        if not history:
            return None
        t1_wins = sum(history)
        games = len(history)
        t1_win_rate = (t1_wins + alpha) / (games + beta)
        return t1_win_rate if rad_id == key[0] else (1.0 - t1_win_rate)
