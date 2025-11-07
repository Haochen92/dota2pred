from typing import Dict, List, Optional, Tuple, NamedTuple

from dota_oracle_common.models.match.table import MatchTable
from dota_oracle_common.models.features import HeroFeaturesTable
from dota_oracle_common.models.histories import HeroDecayedStateTable

from .utils import (
    apply_decay_to_pair,
    extract_hero_picks,
    get_radiant_won,
    sorted_by_start_time,
    ts,
)


class DecayState(NamedTuple):
    wins: float
    games: float
    last_update_ts: int


class BatchHeroWinrateDecayFeatureGenerator:
    """
    Builds hero-level win rate features causally.

    Stateless orchestrator: processes matches chronologically, reads pre-match decayed state
    to compute Bayesian-smoothed win rates (prior_mean/prior_count), emits features, then
    prepares the next state for subsequent matches.
    """

    def generate(
        self,
        all_matches: List[MatchTable],
        *,
        prior_mean: float = 0.5,
        prior_count: float = 2.0,
        half_life_days: float = 45.0,
    ) -> Tuple[List[HeroFeaturesTable], List[HeroDecayedStateTable]]:
        """
        Orchestrates feature generation for a batch of matches.

        Returns:
            - hero_features: list of feature rows (wide format, per slot)
            - history: per-hero decayed state rows after each match they appear in
        """
        if not all_matches:
            return [], []

        hero_states: Dict[int, DecayState] = {}
        rows: List[HeroFeaturesTable] = []
        history: List[HeroDecayedStateTable] = []

        for match in sorted_by_start_time(all_matches):
            row, updates, logs = self._process_one_match(match, hero_states, prior_mean, prior_count, half_life_days)
            # 1) append artifacts
            rows.append(row)
            history.extend(logs)
            # 2) apply state updates
            hero_states.update(updates)

        return rows, history

    def _process_one_match(
        self,
        match: MatchTable,
        current_states: Dict[int, DecayState],
        prior_mean: float,
        prior_count: float,
        half_life_days: float,
    ) -> Tuple[HeroFeaturesTable, Dict[int, DecayState], List[HeroDecayedStateTable]]:
        """
        Orchestrates the two-step process for a single match:
        1) Create features from current state (read phase)
        2) Prepare state updates and logs (write phase)
        """
        row = self._create_feature_row(match, current_states, prior_mean, prior_count, half_life_days)
        updates, logs = self._prepare_updates_and_logs(match, current_states, half_life_days)
        return row, updates, logs

    def _create_feature_row(
        self,
        match: MatchTable,
        current_states: Dict[int, DecayState],
        prior_mean: float,
        prior_count: float,
        half_life_days: float,
    ) -> HeroFeaturesTable:
        now_ts = ts(match.start_time)
        radiant_picks, dire_picks = extract_hero_picks(match)

        def read_wr(hero_id: Optional[int]) -> float:
            state = current_states.get(hero_id) if hero_id is not None else None
            return self._calculate_hero_wr(state, now_ts, prior_mean, prior_count, half_life_days)

        feature_dict = {"match_id": match.match_id}
        for i, hero_id in enumerate(radiant_picks):
            feature_dict[f"hero_{i}_win_rate"] = read_wr(hero_id)
        for i, hero_id in enumerate(dire_picks):
            feature_dict[f"hero_{128 + i}_win_rate"] = read_wr(hero_id)
        return HeroFeaturesTable(**feature_dict)

    def _prepare_updates_and_logs(
        self,
        match: MatchTable,
        current_states: Dict[int, DecayState],
        half_life_days: float,
    ) -> Tuple[Dict[int, DecayState], List[HeroDecayedStateTable]]:
        now_ts = ts(match.start_time)
        updates: Dict[int, DecayState] = {}
        logs: List[HeroDecayedStateTable] = []

        radiant_picks, dire_picks = extract_hero_picks(match)
        radiant_won = get_radiant_won(match)
        if radiant_won is not None:
            all_heroes = radiant_picks + dire_picks
            for idx, hero_id in enumerate(all_heroes):
                if hero_id is None:
                    continue
                hero_won = radiant_won if idx < len(radiant_picks) else (not radiant_won)
                new_state = self._calculate_next_state(current_states.get(hero_id), now_ts, hero_won, half_life_days)
                updates[hero_id] = new_state
                logs.append(
                    HeroDecayedStateTable(
                        hero_id=hero_id,
                        match_id=match.match_id,
                        decayed_wins=new_state.wins,
                        decayed_games=new_state.games,
                        last_update_time=match.start_time,
                    )
                )
        return updates, logs

    # --- Helpers ---
    def _calculate_hero_wr(
        self,
        state: Optional[DecayState],
        now_ts: int,
        prior_mean: float,
        prior_count: float,
        half_life_days: float,
    ) -> float:
        if state is None:
            return prior_mean
        w_wins, w_games, last_ts = state
        w_wins, w_games = apply_decay_to_pair(w_wins, w_games, last_ts, now_ts, half_life_days)
        denom = w_games + prior_count
        if denom <= 1e-6:
            return prior_mean
        return (w_wins + prior_count * prior_mean) / denom

    def _calculate_next_state(
        self,
        state: Optional[DecayState],
        now_ts: int,
        won: bool,
        half_life_days: float,
    ) -> DecayState:
        if state is None:
            decayed_wins, decayed_games = 0.0, 0.0
        else:
            decayed_wins, decayed_games = apply_decay_to_pair(
                state.wins, state.games, state.last_update_ts, now_ts, half_life_days
            )
        return DecayState(
            wins=decayed_wins + (1.0 if won else 0.0),
            games=decayed_games + 1.0,
            last_update_ts=now_ts,
        )
