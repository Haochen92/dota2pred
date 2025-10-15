from typing import Dict, List, Optional, Tuple

from dota_oracle_common.models.match.table import MatchTable

from .models import HeroWinrateTable
from .utils import (
    apply_decay_to_pair,
    default_winrate,
    extract_hero_picks,
    get_radiant_won,
    sorted_by_start_time,
    ts,
)


class HeroWinrateDecayFeatureGenerator:
    """
    Build hero-level winrate features causally (chronological, no leakage).

    Strategy: exponential time-decay histories per hero. Maintains O(1) state
    per hero as (weighted_wins, weighted_games, last_timestamp). For a match,
    features are computed using only the prior state (decayed to now), then the
    state is updated with the outcome, maintaining causal correctness.

    Smoothing:
      - Bayesian smoothing with prior_mean and prior_count:
        (wins + prior_count * prior_mean) / (games + prior_count)
    """

    def generate(
        self,
        all_matches: List[MatchTable],
        *,
        prior_mean: float = 0.5,
        prior_count: float = 2.0,
        half_life_days: float = 45.0,
    ) -> List[HeroWinrateTable]:
        """
        Exponential time decay. Keeps O(1) state per hero: (wins_w, games_w, last_ts).

        - Reads feature values before updating state for the current match.
        - Applies decay from last_ts to now_ts before computing smoothed rate.
        - Applies Bayesian smoothing: (wins + alpha) / (games + beta).
        """
        assert half_life_days > 0, "half_life_days must be positive."
        if not all_matches:
            return []

        matches = sorted_by_start_time(all_matches)
        default_wr = float(prior_mean)

        # hero_id -> (weighted_wins, weighted_games, last_timestamp)
        hero_state: Dict[int, Tuple[float, float, int]] = {}

        rows: List[HeroWinrateTable] = []
        for match in matches:
            cur_ts = ts(match.start_time)
            radiant_picks, dire_picks = extract_hero_picks(match)

            r_wrs = [
                self._read_wr_decay(
                    hero_state.get(h), cur_ts, prior_mean, prior_count, half_life_days, default_wr
                )
                for h in radiant_picks
            ]
            d_wrs = [
                self._read_wr_decay(
                    hero_state.get(h), cur_ts, prior_mean, prior_count, half_life_days, default_wr
                )
                for h in dire_picks
            ]

            row = HeroWinrateTable(**{
                "match_id": match.match_id,
                "radiant_avg_hero_winrate": float(sum(r_wrs) / len(r_wrs)) if r_wrs else default_wr,
                "dire_avg_hero_winrate": float(sum(d_wrs) / len(d_wrs)) if d_wrs else default_wr,
                "radiant_max_hero_winrate": max(r_wrs) if r_wrs else default_wr,
                "dire_max_hero_winrate": max(d_wrs) if d_wrs else default_wr,
            })
            rows.append(row)

            radiant_won = get_radiant_won(match)
            if radiant_won is not None:
                for i, h in enumerate(radiant_picks + dire_picks):
                    player_won = radiant_won if i < len(radiant_picks) else (not radiant_won)
                    hero_state[h] = self._update_state_decay(hero_state.get(h), cur_ts, player_won, half_life_days)

        return rows

    # helpers
    def _read_wr_decay(
        self,
        state: Optional[Tuple[float, float, int]],
        now_ts: int,
        prior_mean: float,
        prior_count: float,
        half_life_days: float,
        default_wr: float,
    ) -> float:
        """
        Convert decayed (wins,games) state into smoothed winrate at time now_ts.
        """
        if state is None:
            return default_wr
        w_wins, w_games, last_ts = state
        w_wins, w_games = apply_decay_to_pair(w_wins, w_games, last_ts, now_ts, half_life_days)
        return (w_wins + prior_count * prior_mean) / (w_games + prior_count)

    def _update_state_decay(
        self,
        state: Optional[Tuple[float, float, int]],
        now_ts: int,
        player_won: bool,
        half_life_days: float,
    ) -> Tuple[float, float, int]:
        """
        Apply decay from last_ts to now_ts, then add this match result.
        """
        if state is None:
            w_wins, w_games, last_ts = 0.0, 0.0, now_ts
        else:
            w_wins, w_games, last_ts = state
            w_wins, w_games = apply_decay_to_pair(w_wins, w_games, last_ts, now_ts, half_life_days)
        w_games += 1.0
        if player_won:
            w_wins += 1.0
        return w_wins, w_games, now_ts
