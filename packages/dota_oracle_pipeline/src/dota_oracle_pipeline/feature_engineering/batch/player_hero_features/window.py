from collections import deque
from typing import Deque, Dict, List, Optional, Tuple

from dota_oracle_common.models.features.table import PlayerHeroFeatureTable
from dota_oracle_common.models.match.table import MatchTable

from .utils import (
    PLAYER_SLOTS,
    RADIANT_SLOTS,
    default_winrate,
    get_player_hero_key,
    get_radiant_won,
    sorted_by_start_time,
)


class PlayerHeroWindowFeatureGenerator:
    """Builds causally-correct player-hero win rate features using a rolling window.

    Generates features using a rolling window for each player-hero history.

    Args:
        alpha (int): Prior wins for Bayesian smoothing.
        beta (int): Prior games for Bayesian smoothing.
        window_size (int): Number of recent games to consider.

    Notes:
        alpha/beta default to 1/2 to set a static uninformative prior win rate of 0.5.
    """

    def generate(
        self,
        all_matches: List[MatchTable],
        *,
        alpha: int = 1,
        beta: int = 2,
        window_size: int = 20,
    ) -> List[PlayerHeroFeatureTable]:
        """Generates features using a sliding window per player-hero pair."""
        assert window_size > 0, "window_size must be a positive integer."
        if not all_matches:
            return []

        matches = sorted_by_start_time(all_matches)
        default_wr = default_winrate(alpha, beta)

        ph_histories: Dict[Tuple[int, int], Deque[bool]] = {}
        features: List[PlayerHeroFeatureTable] = []

        for match in matches:
            # Read features (pre-update) for causal correctness
            fields = self._build_feature_fields_window(
                match, ph_histories, alpha, beta, default_wr
            )
            features.append(PlayerHeroFeatureTable(match_id=match.match_id, **fields))  # type: ignore[arg-type]

            # Update histories only after outcome is known
            radiant_won = get_radiant_won(match)
            if radiant_won is not None:
                for slot in PLAYER_SLOTS:
                    key = get_player_hero_key(match, slot)
                    player_id, hero_id = key
                    if player_id is None or hero_id is None:
                        continue
                    player_won = radiant_won if slot in RADIANT_SLOTS else not radiant_won
                    dq = ph_histories.setdefault((player_id, hero_id), deque(maxlen=window_size))
                    dq.append(player_won)

        return features

    # ---- helpers -----------------------------------------------------------

    def _build_feature_fields_window(
        self,
        match: MatchTable,
        histories: Dict[Tuple[int, int], Deque[bool]],
        alpha: int,
        beta: int,
        default_wr: float,
    ) -> Dict[str, float]:
        """Builds feature fields for a match using rolling-window histories."""
        fields: Dict[str, float] = {}
        for slot in PLAYER_SLOTS:
            key = get_player_hero_key(match, slot)
            history = histories.get(key)
            win_rate = self._read_wr_window(history, alpha, beta, default_wr)
            fields[f"player_hero_{slot}_win_rate"] = win_rate
        return fields

    def _read_wr_window(
        self,
        history: Optional[Deque[bool]],
        alpha: int,
        beta: int,
        default_wr: float,
    ) -> float:
        """Reads win rate from a sliding window of match results."""
        if not history or beta == 0:
            return default_wr
        wins = sum(history)
        games = len(history)
        return (wins + alpha) / (games + beta)
