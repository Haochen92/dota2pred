from typing import Dict, List, Optional, Tuple

from dota_oracle_common.models.features.table import TeamFeaturesTable
from dota_oracle_common.models.match.table import MatchTable

from .utils import (
    apply_decay_to_pair,
    default_winrate,
    get_matchup_key,
    get_matchup_key_and_outcome,
    get_radiant_won,
    sorted_by_start_time,
    ts,
)


class TeamDecayFeatureGenerator:
    """
    Builds causally-correct team-level and matchup win rate features.

    This generator uses a time-weighted (exponentially decayed) history of all
    games for each team and matchup. Features are computed using the decayed
    state prior to the match, then the state is updated after reading, ensuring
    chronological processing and preventing leakage.

    Bayesian smoothing is applied to provide more stable estimates when a team
    or matchup has very little history: (wins + alpha) / (games + beta).
    """

    def generate(
        self,
        all_matches: List[MatchTable],
        *,
        alpha: int = 1,
        beta: int = 2,
        half_life_days: float = 45.0,
    ) -> List[TeamFeaturesTable]:
        """
        Generates features using exponential time decay for team and matchup histories.
        This method gives more weight to recent games.
        """
        assert half_life_days > 0, "half_life_days must be positive."
        if not all_matches:
            return []

        matches = sorted_by_start_time(all_matches)
        default_wr = default_winrate(alpha, beta)

        team_states: Dict[int, Tuple[float, float, int]] = {}
        matchup_states: Dict[Tuple[int, int], Tuple[float, float, int]] = {}

        feature_rows: List[TeamFeaturesTable] = []
        for match in matches:
            now_ts = ts(match.start_time)
            rad_id, dire_id = match.radiant_team_id, match.dire_team_id

            radiant_wr = self._read_wr_decay(team_states.get(rad_id), now_ts, alpha, beta, half_life_days)
            dire_wr = self._read_wr_decay(team_states.get(dire_id), now_ts, alpha, beta, half_life_days)
            matchup_wr = self._read_matchup_wr_decay(matchup_states, rad_id, dire_id, now_ts, alpha, beta, half_life_days)

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
                team_states[rad_id] = self._update_state_decay(team_states.get(rad_id), now_ts, radiant_won, half_life_days)
                team_states[dire_id] = self._update_state_decay(team_states.get(dire_id), now_ts, not radiant_won, half_life_days)

                key, t1_won = get_matchup_key_and_outcome(rad_id, dire_id, radiant_won)
                matchup_states[key] = self._update_state_decay(matchup_states.get(key), now_ts, t1_won, half_life_days)

        return feature_rows

    # helpers
    def _read_wr_decay(
        self, state: Optional[Tuple[float, float, int]], now_ts: int, alpha: int, beta: int, half_life: float
    ) -> Optional[float]:
        """Read a smoothed win rate from a decayed state at `now_ts`."""
        if not state:
            return None
        wins, games, last_ts = state
        wins, games = apply_decay_to_pair(wins, games, last_ts, now_ts, half_life)
        if (games + beta) == 0:
            return None
        return (wins + alpha) / (games + beta)

    def _read_matchup_wr_decay(
        self,
        states: Dict[Tuple[int, int], Tuple[float, float, int]],
        rad_id: int,
        dire_id: int,
        now_ts: int,
        alpha: int,
        beta: int,
        half_life: float,
    ) -> Optional[float]:
        """Read a smoothed matchup win rate (Radiant perspective) from decayed state."""
        key = get_matchup_key(rad_id, dire_id)
        state = states.get(key)
        if not state:
            return None
        t1_wins, games, last_ts = state
        t1_wins, games = apply_decay_to_pair(t1_wins, games, last_ts, now_ts, half_life)
        if (games + beta) == 0:
            return None
        t1_win_rate = (t1_wins + alpha) / (games + beta)
        return t1_win_rate if rad_id == key[0] else (1.0 - t1_win_rate)

    def _update_state_decay(
        self, state: Optional[Tuple[float, float, int]], now_ts: int, won: bool, half_life: float
    ) -> Tuple[float, float, int]:
        """Apply decay from last_ts to now_ts, then add this match result."""
        if state is None:
            wins, games, last_ts = 0.0, 0.0, now_ts
        else:
            wins, games, last_ts = state
            wins, games = apply_decay_to_pair(wins, games, last_ts, now_ts, half_life)
        games += 1.0
        if won:
            wins += 1.0
        return wins, games, now_ts
