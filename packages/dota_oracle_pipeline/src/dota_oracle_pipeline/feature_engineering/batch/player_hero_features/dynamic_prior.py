from typing import Dict, List, Tuple, Optional

from dota_oracle_common.models.features.table import PlayerHeroFeatureTable
from dota_oracle_common.models.match.table import MatchTable
from dota_oracle_common.models.histories import PlayerHeroDecayedStateTable

from .utils import (
    PLAYER_SLOTS,
    RADIANT_SLOTS,
    PlayerHeroDecayState,
    get_player_hero_key,
    get_radiant_won,
    read_wr_decay,
    read_wr_decay_dynamic,
    sorted_by_start_time,
    ts,
    update_state_decay,
)


class BatchPlayerHeroDynamicPriorFeatureGenerator:
    """
    Stateless generator that blends player-hero history with dynamic hero priors.

    Two-phase orchestrator:
    1) Generate dynamic hero priors per match from decayed global hero performance.
    2) Process matches chronologically; for each, read pre-match player-hero decayed state
       with the match-specific hero prior to compute a smoothed win rate; then prepare
       next state updates and historical logs.
    """

    def generate(
        self,
        all_matches: List[MatchTable],
        *,
        player_prior_count: float = 20.0,
        player_half_life_days: float = 45.0,
        hero_prior_mean: float = 0.50,
        hero_prior_count: float = 15.0,
        hero_half_life_days: float = 90.0,
        verbose: bool = True,
    ) -> Tuple[List[PlayerHeroFeatureTable], List[PlayerHeroDecayedStateTable]]:
        """
        Returns:
            - player_hero_features: list of feature rows per match
            - history: per-(player,hero) decayed state rows after each applicable match
        """
        if not all_matches:
            return [], []

        matches = sorted_by_start_time(all_matches)

        if verbose:
            print("Step 1/2: Generating dynamic hero priors...")
        hero_priors = self._generate_hero_priors(
            matches,
            prior_mean=hero_prior_mean,
            prior_count=hero_prior_count,
            half_life_days=hero_half_life_days,
        )
        if verbose:
            print("Hero priors generated.")

        if verbose:
            print("Step 2/2: Generating player-hero features with dynamic priors...")

        ph_states: Dict[Tuple[int, int], PlayerHeroDecayState] = {}
        features: List[PlayerHeroFeatureTable] = []
        history: List[PlayerHeroDecayedStateTable] = []

        for match in matches:
            row, updates, logs = self._process_one_match(
                match,
                ph_states,
                hero_priors.get(match.match_id, {}),
                player_prior_count,
                player_half_life_days,
            )
            # 1) append artifacts
            features.append(row)
            history.extend(logs)
            # 2) apply updates
            ph_states.update(updates)

        if verbose:
            print("Player-hero features generated.")

        return features, history

    # ---- hero priors -------------------------------------------------------

    def _generate_hero_priors(
        self,
        sorted_matches: List[MatchTable],
        *,
        prior_mean: float,
        prior_count: float,
        half_life_days: float,
    ) -> Dict[int, Dict[int, float]]:
        """Generates per-match hero priors from decayed global hero performance."""
        default_wr = float(prior_mean)
        hero_state: Dict[int, PlayerHeroDecayState] = {}
        priors_lookup: Dict[int, Dict[int, float]] = {}

        for match in sorted_matches:
            cur_ts = ts(match.start_time)
            priors_lookup[match.match_id] = {}

            # Collect all heroes present in the match
            all_hero_ids_in_match = set()
            for slot in PLAYER_SLOTS:
                _, hero_id = get_player_hero_key(match, slot)
                if hero_id is not None:
                    all_hero_ids_in_match.add(hero_id)

            # Read priors before updating state (causal)
            for hero_id in all_hero_ids_in_match:
                win_rate = read_wr_decay(
                    hero_state.get(hero_id), cur_ts, prior_mean, prior_count, half_life_days, default_wr
                )
                priors_lookup[match.match_id][hero_id] = win_rate

            # Update hero-level states based on outcome
            radiant_won = get_radiant_won(match)
            if radiant_won is not None:
                for slot in PLAYER_SLOTS:
                    _, hero_id = get_player_hero_key(match, slot)
                    if hero_id is not None:
                        player_won = radiant_won if slot in RADIANT_SLOTS else not radiant_won
                        prev_state: Optional[PlayerHeroDecayState] = hero_state.get(hero_id)
                        hero_state[hero_id] = update_state_decay(prev_state, cur_ts, player_won, half_life_days)

        return priors_lookup

    # ---- per-match processing ---------------------------------------------

    def _process_one_match(
        self,
        match: MatchTable,
        current_states: Dict[Tuple[int, int], PlayerHeroDecayState],
        match_priors: Dict[int, float],
        player_prior_count: float,
        player_half_life_days: float,
    ) -> Tuple[PlayerHeroFeatureTable, Dict[Tuple[int, int], PlayerHeroDecayState], List[PlayerHeroDecayedStateTable]]:
        """
        1) Create the feature row using match-specific hero priors
        2) Prepare state updates and logs based on outcome
        """
        row = self._create_feature_row(
            match,
            current_states,
            match_priors,
            player_prior_count,
            player_half_life_days,
        )
        updates, logs = self._prepare_updates_and_logs(match, current_states, player_half_life_days)
        return row, updates, logs

    def _create_feature_row(
        self,
        match: MatchTable,
        current_states: Dict[Tuple[int, int], PlayerHeroDecayState],
        match_priors: Dict[int, float],
        player_prior_count: float,
        player_half_life_days: float,
    ) -> PlayerHeroFeatureTable:
        now_ts = ts(match.start_time)
        fields: Dict[str, float] = {}
        for slot in PLAYER_SLOTS:
            key = get_player_hero_key(match, slot)
            account_id, hero_id = key
            if account_id is None or hero_id is None:
                fields[f"player_hero_{slot}_win_rate"] = 0.5
                continue
            state = current_states.get(key)
            prior_rate = match_priors.get(hero_id, 0.5)
            fields[f"player_hero_{slot}_win_rate"] = read_wr_decay_dynamic(
                state, now_ts, player_prior_count, player_half_life_days, prior_rate
            )
        return PlayerHeroFeatureTable(match_id=match.match_id, **fields)

    def _prepare_updates_and_logs(
        self,
        match: MatchTable,
        current_states: Dict[Tuple[int, int], PlayerHeroDecayState],
        player_half_life_days: float,
    ) -> Tuple[Dict[Tuple[int, int], PlayerHeroDecayState], List[PlayerHeroDecayedStateTable]]:
        now_ts = ts(match.start_time)
        updates: Dict[Tuple[int, int], PlayerHeroDecayState] = {}
        logs: List[PlayerHeroDecayedStateTable] = []
        radiant_won = get_radiant_won(match)
        if radiant_won is not None:
            for slot in PLAYER_SLOTS:
                key = get_player_hero_key(match, slot)
                account_id, hero_id = key
                if account_id is None or hero_id is None:
                    continue
                player_won = radiant_won if slot in RADIANT_SLOTS else not radiant_won
                new_state = self._calculate_next_state(
                    current_states.get(key), now_ts, player_won, player_half_life_days
                )
                updates[key] = new_state
                logs.append(
                    PlayerHeroDecayedStateTable(
                        account_id=account_id,
                        hero_id=hero_id,
                        match_id=match.match_id,
                        decayed_wins=new_state.weighted_wins,
                        decayed_games=new_state.weighted_games,
                        last_update_time=match.start_time,
                    )
                )
        return updates, logs

    def _calculate_next_state(
        self,
        state: Optional[PlayerHeroDecayState],
        now_ts: int,
        player_won: bool,
        player_half_life_days: float,
    ) -> PlayerHeroDecayState:
        return update_state_decay(state, now_ts, player_won, player_half_life_days)
