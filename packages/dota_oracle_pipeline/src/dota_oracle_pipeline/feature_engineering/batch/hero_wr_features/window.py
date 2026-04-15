from collections import deque
from typing import Deque, Dict, List

from dota_oracle_common.models.match.table import MatchTable

from .models import HeroWinrateTable
from .utils import (
    default_winrate,
    extract_hero_picks,
    get_radiant_won,
    sorted_by_start_time,
)


class HeroWinrateWindowFeatureGenerator:
    """
    Build hero-level winrate features causally (chronological, no leakage).

    Strategy: rolling K-last window histories per hero using an in-memory deque
    of booleans (True=win, False=loss). Features for a match are computed using
    only the history BEFORE that match, then the state is updated with the
    outcome — preserving causal correctness and preventing leakage.

    Smoothing:
      - Bayesian smoothing (alpha/beta) is applied at read time:
        (wins + alpha) / (games + beta)
    """

    def generate(
        self,
        all_matches: List[MatchTable],
        *,
        alpha: int = 1,
        beta: int = 2,
        window_size: int = 20,
    ) -> List[HeroWinrateTable]:
        """
        Rolling K-last window per hero using a deque of booleans.

        - Keeps a bounded deque per hero with capacity `window_size`.
        - Reads feature values before updating state for the current match.
        - Applies Bayesian smoothing: (wins + alpha) / (games + beta).
        """
        assert window_size > 0, "window_size must be a positive integer."
        if not all_matches:
            return []

        matches = sorted_by_start_time(all_matches)
        default_wr = default_winrate(alpha, beta)

        # hero_id -> deque[bool] (win history capped at window_size)
        hero_history: Dict[int, Deque[bool]] = {}

        rows: List[HeroWinrateTable] = []
        for match in matches:
            radiant_picks, dire_picks = extract_hero_picks(match)

            r_wrs = [self._read_wr_window(hero_history.get(h), alpha, beta) for h in radiant_picks]
            d_wrs = [self._read_wr_window(hero_history.get(h), alpha, beta) for h in dire_picks]

            row = HeroWinrateTable(
                **{
                    **{
                        "match_id": match.match_id,
                    },
                    **{
                        "radiant_avg_hero_winrate": float(sum(r_wrs) / len(r_wrs)) if r_wrs else default_wr,
                        "dire_avg_hero_winrate": float(sum(d_wrs) / len(d_wrs)) if d_wrs else default_wr,
                        "radiant_max_hero_winrate": max(r_wrs) if r_wrs else default_wr,
                        "dire_max_hero_winrate": max(d_wrs) if d_wrs else default_wr,
                    },
                }
            )
            rows.append(row)

            radiant_won = get_radiant_won(match)
            if radiant_won is not None:
                # Update AFTER reading
                for i, h in enumerate(radiant_picks + dire_picks):
                    player_won = radiant_won if i < len(radiant_picks) else (not radiant_won)
                    dq = hero_history.setdefault(h, deque(maxlen=window_size))
                    dq.append(player_won)

        return rows

    def _read_wr_window(self, history: Deque[bool] | None, alpha: int, beta: int) -> float:
        """Convert boolean history (wins) into smoothed winrate."""
        if not history:
            return default_winrate(alpha, beta)
        wins = sum(history)
        games = len(history)
        return (wins + alpha) / (games + beta)
