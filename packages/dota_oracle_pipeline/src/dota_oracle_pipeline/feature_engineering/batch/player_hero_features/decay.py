from typing import Dict, List, Optional, Tuple

from dota_oracle_common.models.features.table import PlayerHeroFeatureTable
from dota_oracle_common.models.match.table import MatchTable

from .utils import (
    PLAYER_SLOTS,
    RADIANT_SLOTS,
    PlayerHeroDecayState,
    get_player_hero_key,
    get_radiant_won,
    read_wr_decay,
    sorted_by_start_time,
    ts,
    update_state_decay,
)


class BatchPlayerHeroDecayFeatureGenerator:
    """
    Stateless generator for player-hero win rate features using exponential time decay.

    Processes matches chronologically. For each match, reads pre-match decayed player-hero
    state to compute Bayesian-smoothed win rates (prior_mean/prior_count), emits features,
    then prepares next state updates based on the outcome.
    """

    def generate(
        self,
        all_matches: List[MatchTable],
        *,
        prior_mean: float = 0.5,
        prior_count: float = 2.0,
        half_life_days: float = 45.0,
    ) -> List[PlayerHeroFeatureTable]:
        """
        Returns a list of PlayerHeroFeatureTable rows, one per match.
        """
        if not all_matches:
            return []

        ph_states: Dict[Tuple[int, int], PlayerHeroDecayState] = {}
        features: List[PlayerHeroFeatureTable] = []

        for match in sorted_by_start_time(all_matches):
            row, updates = self._process_one_match(match, ph_states, prior_mean, prior_count, half_life_days)
            # 1) append feature row
            features.append(row)
            # 2) apply state updates
            ph_states.update(updates)

        return features

    def _process_one_match(
        self,
        match: MatchTable,
        current_states: Dict[Tuple[int, int], PlayerHeroDecayState],
        prior_mean: float,
        prior_count: float,
        half_life_days: float,
    ) -> Tuple[PlayerHeroFeatureTable, Dict[Tuple[int, int], PlayerHeroDecayState]]:
        """
        1) Create the feature row from current state
        2) Prepare state updates based on match outcome
        """
        row = self._create_feature_row(match, current_states, prior_mean, prior_count, half_life_days)
        updates = self._prepare_updates(match, current_states, half_life_days)
        return row, updates

    def _create_feature_row(
        self,
        match: MatchTable,
        current_states: Dict[Tuple[int, int], PlayerHeroDecayState],
        prior_mean: float,
        prior_count: float,
        half_life_days: float,
    ) -> PlayerHeroFeatureTable:
        now_timestamp = ts(match.start_time)
        fields: Dict[str, float] = {}
        default_wr = prior_mean
        for slot in PLAYER_SLOTS:
            key = get_player_hero_key(match, slot)
            state = current_states.get(key)
            fields[f"player_hero_{slot}_win_rate"] = read_wr_decay(
                state, now_timestamp, prior_mean, prior_count, half_life_days, default_wr
            )
        return PlayerHeroFeatureTable(match_id=match.match_id, **fields)  # type: ignore[arg-type]

    def _prepare_updates(
        self,
        match: MatchTable,
        current_states: Dict[Tuple[int, int], PlayerHeroDecayState],
        half_life_days: float,
    ) -> Dict[Tuple[int, int], PlayerHeroDecayState]:
        now_timestamp = ts(match.start_time)
        updates: Dict[Tuple[int, int], PlayerHeroDecayState] = {}
        radiant_won = get_radiant_won(match)
        if radiant_won is not None:
            for slot in PLAYER_SLOTS:
                key = get_player_hero_key(match, slot)
                player_id, hero_id = key
                if player_id is None or hero_id is None:
                    continue
                player_won = radiant_won if slot in RADIANT_SLOTS else not radiant_won
                updates[(player_id, hero_id)] = self._calculate_next_state(
                    current_states.get((player_id, hero_id)), now_timestamp, player_won, half_life_days
                )
        return updates

    def _calculate_next_state(
        self,
        state: Optional[PlayerHeroDecayState],
        now_ts: int,
        player_won: bool,
        half_life_days: float,
    ) -> PlayerHeroDecayState:
        # Thin wrapper to keep naming consistent with other modules
        return update_state_decay(state, now_ts, player_won, half_life_days)
