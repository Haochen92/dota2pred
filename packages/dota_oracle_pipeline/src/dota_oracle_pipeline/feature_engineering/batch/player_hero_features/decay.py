from typing import Dict, List, Optional, Tuple

from dota_oracle_common.models.features.table import PlayerHeroFeatureTable
from dota_oracle_common.models.match.table import MatchTable

from .utils import (
    PLAYER_SLOTS,
    RADIANT_SLOTS,
    PlayerHeroDecayState,
    default_winrate,
    get_player_hero_key,
    get_radiant_won,
    read_wr_decay,
    sorted_by_start_time,
    ts,
    update_state_decay,
)


class PlayerHeroDecayFeatureGenerator:
    """Builds features using exponential time decay for player-hero histories.

    Generates features using exponential time decay for each player-hero history.

    Args:
        alpha (int): Prior wins for Bayesian smoothing.
        beta (int): Prior games for Bayesian smoothing.
        half_life_days (float): Half-life in days for exponential decay.

    Notes:
        alpha/beta default to 1/2 to set a static uninformative prior win rate of 0.5.
    """

    def generate(
        self,
        all_matches: List[MatchTable],
        *,
        alpha: int = 1,
        beta: int = 2,
        half_life_days: float = 45.0,
    ) -> List[PlayerHeroFeatureTable]:
        """Generates features using exponential decay per player-hero pair."""
        assert half_life_days > 0, "half_life_days must be positive."
        if not all_matches:
            return []

        matches = sorted_by_start_time(all_matches)
        default_wr = default_winrate(alpha, beta)

        ph_states: Dict[Tuple[int, int], PlayerHeroDecayState] = {}
        features: List[PlayerHeroFeatureTable] = []

        for match in matches:
            now_timestamp = ts(match.start_time)

            # Read features (pre-update) for causal correctness
            fields: Dict[str, float] = {}
            for slot in PLAYER_SLOTS:
                key = get_player_hero_key(match, slot)
                state = ph_states.get(key)
                win_rate = read_wr_decay(
                    state, now_timestamp, alpha, beta, half_life_days, default_wr
                )
                fields[f"player_hero_{slot}_win_rate"] = win_rate
            features.append(PlayerHeroFeatureTable(match_id=match.match_id, **fields))  # type: ignore[arg-type]

            # Update states after outcome is known
            radiant_won = get_radiant_won(match)
            if radiant_won is not None:
                for slot in PLAYER_SLOTS:
                    key = get_player_hero_key(match, slot)
                    player_id, hero_id = key
                    if player_id is None or hero_id is None:
                        continue
                    player_won = radiant_won if slot in RADIANT_SLOTS else not radiant_won
                    ph_states[(player_id, hero_id)] = update_state_decay(
                        ph_states.get((player_id, hero_id)), now_timestamp, player_won, half_life_days
                    )

        return features
