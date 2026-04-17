from typing import Dict, List, Optional, Tuple, NamedTuple

from dota_oracle_common.models.features.table import TeamFeaturesTable
from dota_oracle_common.models.match.table import MatchTable
from dota_oracle_common.models.histories import (
    TeamDecayedStateTable,
    TeamMatchupDecayedStateTable,
)

from .utils import (
    apply_decay_to_pair,
    get_matchup_key,
    get_matchup_key_and_outcome,
    get_radiant_won,
    sorted_by_start_time,
    ts,
)


class DecayState(NamedTuple):
    """Represents the decayed state of a team or matchup."""

    wins: float
    games: float
    last_update_ts: int


# Value to avoid division by zero
EPSILON = 1e-6


class BatchTeamDecayFeatureGenerator:
    """
    Builds causally-correct team-level and matchup win rate features for a batch of matches.

    This class is stateless across calls to `generate`. It processes matches chronologically,
    reads decayed state to form features for each match, then updates state for the next match.
    """

    def generate(
        self,
        all_matches: List[MatchTable],
        *,
        prior_mean: float = 0.5,
        prior_count: float = 2.0,
        half_life_days: float = 45.0,
    ) -> Tuple[List[TeamFeaturesTable], List[TeamDecayedStateTable], List[TeamMatchupDecayedStateTable]]:
        """
        Orchestrates feature generation for an entire batch of matches.
        Incrementally process each match in chronological order, starting from the earliest match.
        Create features using decayed states from prior matches, then update states based on current match outcomes.

        Returns:
            - team feature rows for each match
            - per-team decayed state history (one row per team per match they played)
            - per-matchup decayed state history (one row per affected matchup per match)
        """
        if not all_matches:
            return [], [], []

        # Local state ensures no cross-call leakage
        team_states: Dict[int, DecayState] = {}
        matchup_states: Dict[Tuple[int, int], DecayState] = {}

        feature_rows: List[TeamFeaturesTable] = []
        team_history: List[TeamDecayedStateTable] = []
        matchup_history: List[TeamMatchupDecayedStateTable] = []

        for match in sorted_by_start_time(all_matches):
            (
                features,
                team_updates,
                matchup_update,
                team_logs,
                matchup_log,
            ) = self._process_one_match(
                match,
                team_states,
                matchup_states,
                prior_mean,
                prior_count,
                half_life_days,
            )

            # 1. Append artifacts
            feature_rows.append(features)
            team_history.extend(team_logs)
            if matchup_log:
                matchup_history.append(matchup_log)

            # 2. Apply state updates
            team_states.update(team_updates)
            if matchup_update:
                matchup_states.update(matchup_update)

        return feature_rows, team_history, matchup_history

    def _process_one_match(
        self,
        match: MatchTable,
        current_team_states: Dict[int, DecayState],
        current_matchup_states: Dict[Tuple[int, int], DecayState],
        prior_mean: float,
        prior_count: float,
        half_life_days: float,
    ) -> Tuple[
        TeamFeaturesTable,
        Dict[int, DecayState],
        Dict[Tuple[int, int], DecayState],
        List[TeamDecayedStateTable],
        Optional[TeamMatchupDecayedStateTable],
    ]:
        """Processes a single match and returns artifacts for features, states, and logs."""
        # 1) Create features using current state (read phase)
        feature_row = self._create_feature_row(
            match,
            current_team_states,
            current_matchup_states,
            prior_mean,
            prior_count,
            half_life_days,
        )

        # 2) Prepare updates and logs (write phase)
        team_updates, matchup_update, team_logs, matchup_log = self._prepare_updates_and_logs(
            match,
            current_team_states,
            current_matchup_states,
            half_life_days,
        )

        return feature_row, team_updates, matchup_update, team_logs, matchup_log

    def _create_feature_row(
        self,
        match: MatchTable,
        current_team_states: Dict[int, DecayState],
        current_matchup_states: Dict[Tuple[int, int], DecayState],
        prior_mean: float,
        prior_count: float,
        half_life_days: float,
    ) -> TeamFeaturesTable:
        """Creates a feature row for a match by reading from the current states."""
        now_ts = ts(match.start_time)
        radiant_id = match.radiant_team_id
        dire_id = match.dire_team_id

        radiant_wr = (
            self._calculate_team_win_rate(
                current_team_states.get(radiant_id), now_ts, prior_mean, prior_count, half_life_days
            )
            if radiant_id
            else prior_mean
        )
        dire_wr = (
            self._calculate_team_win_rate(
                current_team_states.get(dire_id), now_ts, prior_mean, prior_count, half_life_days
            )
            if dire_id
            else prior_mean
        )
        matchup_wr = (
            self._calculate_matchup_win_rate(
                current_matchup_states, radiant_id, dire_id, now_ts, prior_mean, prior_count, half_life_days
            )
            if (radiant_id and dire_id)
            else prior_mean
        )

        return TeamFeaturesTable(
            match_id=match.match_id,
            radiant_win_rate=radiant_wr,
            dire_win_rate=dire_wr,
            radiant_dire_matchup=matchup_wr,
        )

    def _prepare_updates_and_logs(
        self,
        match: MatchTable,
        current_team_states: Dict[int, DecayState],
        current_matchup_states: Dict[Tuple[int, int], DecayState],
        half_life_days: float,
    ) -> Tuple[
        Dict[int, DecayState],
        Dict[Tuple[int, int], DecayState],
        List[TeamDecayedStateTable],
        Optional[TeamMatchupDecayedStateTable],
    ]:
        """
        Calculate the next states based on current match outcome, update temporal states and prepare logs.

        Args:
            match (MatchTable): The match being processed.
            current_team_states (Dict[int, DecayState]): Current decayed states for teams.
            current_matchup_states (Dict[Tuple[int, int], DecayState]): Current decayed states for matchups.
            half_life_days (float): Half-life in days for decay calculation.

        Returns:
            - team_updates (Dict[int, DecayState]): Updated decayed states for teams.
            - matchup_update (Dict[Tuple[int, int], DecayState]): Updated decayed states for matchups.
            - team_logs (List[TeamDecayedStateTable]): Logs of team decayed states.
            - matchup_log (Optional[TeamMatchupDecayedStateTable]): Log of matchup decayed state if applicable.
        """
        now_ts = ts(match.start_time)
        radiant_id = match.radiant_team_id
        dire_id = match.dire_team_id

        team_updates: Dict[int, DecayState] = {}
        matchup_update: Dict[Tuple[int, int], DecayState] = {}
        team_logs: List[TeamDecayedStateTable] = []
        matchup_log: Optional[TeamMatchupDecayedStateTable] = None

        radiant_won = get_radiant_won(match)
        if radiant_won is not None and radiant_id and dire_id:
            # Radiant team
            rad_state_new = self._calculate_next_state(
                current_team_states.get(radiant_id), now_ts, radiant_won, half_life_days
            )
            team_updates[radiant_id] = rad_state_new
            team_logs.append(
                self._create_team_log(match, radiant_id, getattr(match, "radiant_name", None), rad_state_new)
            )

            # Dire team
            dire_state_new = self._calculate_next_state(
                current_team_states.get(dire_id), now_ts, not radiant_won, half_life_days
            )
            team_updates[dire_id] = dire_state_new
            team_logs.append(self._create_team_log(match, dire_id, getattr(match, "dire_name", None), dire_state_new))

            # Matchup
            if radiant_id != dire_id:
                matchup_key, t1_won = get_matchup_key_and_outcome(radiant_id, dire_id, radiant_won)
                matchup_state_new = self._calculate_next_state(
                    current_matchup_states.get(matchup_key), now_ts, t1_won, half_life_days
                )
                matchup_update[matchup_key] = matchup_state_new
                matchup_log = self._create_matchup_log(match, matchup_key, matchup_state_new)

        return team_updates, matchup_update, team_logs, matchup_log

    # --- Helpers ---

    def _calculate_team_win_rate(
        self,
        state: Optional[DecayState],
        now_ts: int,
        prior_mean: float,
        prior_count: float,
        half_life: float,
    ) -> float:
        if state is None:
            return prior_mean
        wins, games, last_ts = state
        decayed_wins, decayed_games = apply_decay_to_pair(wins, games, last_ts, now_ts, half_life)
        denom = decayed_games + prior_count
        if denom <= EPSILON:
            return prior_mean
        return (decayed_wins + prior_count * prior_mean) / denom

    def _calculate_matchup_win_rate(
        self,
        states: Dict[Tuple[int, int], DecayState],
        rad_id: Optional[int],
        dire_id: Optional[int],
        now_ts: int,
        prior_mean: float,
        prior_count: float,
        half_life: float,
    ) -> float:
        if not (rad_id and dire_id):
            return prior_mean
        key = get_matchup_key(rad_id, dire_id)
        state = states.get(key)
        if not state:
            return prior_mean
        t1_wins, games, last_ts = state
        decayed_t1_wins, decayed_games = apply_decay_to_pair(t1_wins, games, last_ts, now_ts, half_life)
        denom = decayed_games + prior_count
        if denom <= EPSILON:
            return prior_mean
        t1_wr = (decayed_t1_wins + prior_count * prior_mean) / denom
        return t1_wr if rad_id == key[0] else (1.0 - t1_wr)

    def _calculate_next_state(
        self, state: Optional[DecayState], now_ts: int, won: bool, half_life: float
    ) -> DecayState:
        if state is None:
            decayed_wins, decayed_games = 0.0, 0.0
        else:
            decayed_wins, decayed_games = apply_decay_to_pair(
                state.wins, state.games, state.last_update_ts, now_ts, half_life
            )
        return DecayState(
            wins=decayed_wins + (1.0 if won else 0.0),
            games=decayed_games + 1.0,
            last_update_ts=now_ts,
        )

    def _create_team_log(
        self, match: MatchTable, team_id: int, team_name: Optional[str], new_state: DecayState
    ) -> TeamDecayedStateTable:
        return TeamDecayedStateTable(
            team_id=team_id,
            team_name=team_name,
            match_id=match.match_id,
            decayed_wins=new_state.wins,
            decayed_games=new_state.games,
            last_update_time=match.start_time,
        )

    def _create_matchup_log(
        self, match: MatchTable, matchup_key: Tuple[int, int], new_state: DecayState
    ) -> TeamMatchupDecayedStateTable:
        t1_id, t2_id = matchup_key
        rad_name, dire_name = getattr(match, "radiant_name", None), getattr(match, "dire_name", None)
        t1_name, t2_name = (rad_name, dire_name) if match.radiant_team_id == t1_id else (dire_name, rad_name)

        return TeamMatchupDecayedStateTable(
            team1_id=t1_id,
            team2_id=t2_id,
            team1_name=t1_name,
            team2_name=t2_name,
            match_id=match.match_id,
            decayed_t1_wins=new_state.wins,
            decayed_games=new_state.games,
            last_update_time=match.start_time,
        )
