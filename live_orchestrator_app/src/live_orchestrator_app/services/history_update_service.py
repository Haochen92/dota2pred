from typing import List

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from dota_oracle_common.repositories.history_repository import HistoryRepository
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.utils import get_logger
from dota_oracle_common.utils.time_utils import to_utc_datetime_object
from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.models.histories import (
    TeamDecayedStateTable,
    TeamMatchupDecayedStateTable,
    PlayerHeroDecayedStateTable,
    HeroDecayedStateTable,
)
from dota_oracle_common.constants.hyperparam_config import (
    TEAM_FEATURES_HYPERPARAMS,
    HERO_FEATURES_HYPERPARAMS,
    PLAYER_HERO_FEATURES_HYPERPARAMS,
)
from dota_oracle_pipeline.feature_engineering.decay_utils import apply_decay_to_pair

logger = get_logger(__name__)


class HistoryUpdateService:
    """
    Service responsible for updating the decayed state history tables after a match is completed.
    Each public method operates within its own transaction to ensure atomicity.
    """

    async def update_all_histories_for_match(
        self, db_session_factory: async_sessionmaker[AsyncSession], match_id: int
    ) -> None:
        """
        Atomically updates all decayed history states (team, matchup, player-hero, hero)
        for a single completed match. If any part fails, the entire transaction is rolled back.
        """
        logger.info(f"Starting atomic history update for match {match_id}")

        async with db_session_factory() as session:
            async with session.begin():
                try:
                    history_repo = HistoryRepository(session)
                    match = await self._get_completed_match_details(match_id, session)

                    await self._update_team_states(history_repo, match)
                    await self._update_team_matchup_state(history_repo, match)
                    await self._update_player_and_hero_states(history_repo, match)

                    logger.info(f"Successfully committed all history updates for match {match_id}.")

                except Exception as e:
                    logger.error(
                        f"History update transaction failed for match {match_id}. "
                        f"All changes will be rolled back. Error: {e}",
                        exc_info=True,
                    )
                    raise

    async def _update_team_states(self, history_repo: HistoryRepository, match: MatchTable) -> None:
        """Calculates and upserts the decayed win/loss states for the two teams in the match."""
        if not match.radiant_team_id and not match.dire_team_id:
            return

        match_start_time = to_utc_datetime_object(match.start_time)
        match_start_ts = int(match_start_time.timestamp())
        half_life_days = float(TEAM_FEATURES_HYPERPARAMS.half_life_days)

        teams_to_update = [
            {"id": match.radiant_team_id, "name": match.radiant_name, "won": match.outcome.radiant_win},
            {"id": match.dire_team_id, "name": match.dire_name, "won": not match.outcome.radiant_win},
        ]

        new_team_states: List[TeamDecayedStateTable] = []
        processed_ids = set()
        for team_info in teams_to_update:
            team_id = team_info["id"]
            if not team_id or team_id in processed_ids:
                continue
            processed_ids.add(team_id)

            previous_state = await history_repo.get_team_state_before_by_id(team_id, match_start_time)

            if previous_state:
                decayed_wins, decayed_games = apply_decay_to_pair(
                    previous_state.decayed_wins,
                    previous_state.decayed_games,
                    int(previous_state.last_update_time.timestamp()),
                    match_start_ts,
                    half_life_days,
                )
            else:
                decayed_wins, decayed_games = 0.0, 0.0

            decayed_games += 1.0
            if team_info["won"]:
                decayed_wins += 1.0

            new_team_states.append(
                TeamDecayedStateTable(
                    team_id=team_id,
                    match_id=match.match_id,
                    team_name=team_info["name"],
                    decayed_wins=decayed_wins,
                    decayed_games=decayed_games,
                    last_update_time=match_start_time,
                )
            )

        if new_team_states:
            await history_repo.upsert_team_decayed_states(new_team_states)
            logger.debug(f"Upserted {len(new_team_states)} team states for match {match.match_id}")

    async def _update_team_matchup_state(self, history_repo: HistoryRepository, match: MatchTable) -> None:
        """Calculates and upserts the decayed state for the head-to-head matchup."""
        radiant_id, dire_id = match.radiant_team_id, match.dire_team_id
        if not radiant_id or not dire_id or radiant_id == dire_id:
            return

        match_start_time = to_utc_datetime_object(match.start_time)
        match_start_ts = int(match_start_time.timestamp())
        half_life_days = float(TEAM_FEATURES_HYPERPARAMS.half_life_days)

        team1_id, team2_id = sorted([radiant_id, dire_id])
        team1_name = match.radiant_name if radiant_id == team1_id else match.dire_name
        team2_name = match.dire_name if dire_id == team2_id else match.radiant_name

        previous_state = await history_repo.get_team_matchup_state_before_by_id(team1_id, team2_id, match_start_time)

        if previous_state:
            decayed_t1_wins, decayed_games = apply_decay_to_pair(
                previous_state.decayed_t1_wins,
                previous_state.decayed_games,
                int(previous_state.last_update_time.timestamp()),
                match_start_ts,
                half_life_days,
            )
        else:
            decayed_t1_wins, decayed_games = 0.0, 0.0

        team1_won_this_match = (match.outcome.radiant_win and radiant_id == team1_id) or (
            not match.outcome.radiant_win and dire_id == team1_id
        )

        decayed_games += 1.0
        if team1_won_this_match:
            decayed_t1_wins += 1.0

        new_matchup_state = TeamMatchupDecayedStateTable(
            team1_id=team1_id,
            team2_id=team2_id,
            match_id=match.match_id,
            team1_name=team1_name,
            team2_name=team2_name,
            decayed_t1_wins=decayed_t1_wins,
            decayed_games=decayed_games,
            last_update_time=match_start_time,
        )

        await history_repo.upsert_team_matchup_decayed_states([new_matchup_state])
        logger.debug(f"Upserted 1 team matchup state for match {match.match_id}")

    async def _update_player_and_hero_states(self, history_repo: HistoryRepository, match: MatchTable) -> None:
        """
        Calculates and upserts decayed states for all 10 player-hero combinations
        and the 10 corresponding hero appearances in the match.
        """
        match_start_time = to_utc_datetime_object(match.start_time)
        match_start_ts = int(match_start_time.timestamp())
        hero_hl = float(HERO_FEATURES_HYPERPARAMS.half_life_days)
        player_hero_hl = float(PLAYER_HERO_FEATURES_HYPERPARAMS.player_half_life_days)
        radiant_won = match.outcome.radiant_win

        player_slots = list(range(5)) + list(range(128, 133))
        new_ph_states: List[PlayerHeroDecayedStateTable] = []
        new_hero_states: List[HeroDecayedStateTable] = []

        for slot in player_slots:
            account_id = getattr(match, f"slot_{slot}_account_id")
            hero_id = getattr(match, f"slot_{slot}_hero_id")
            if not account_id or not hero_id:
                continue

            player_won_this_match = radiant_won if slot < 5 else not radiant_won

            prev_ph_state = await history_repo.get_player_hero_state_before(account_id, hero_id, match_start_time)
            ph_wins, ph_games = self._decay_and_update_state(
                prev_ph_state, match_start_ts, player_hero_hl, player_won_this_match
            )
            new_ph_states.append(
                PlayerHeroDecayedStateTable(
                    account_id=account_id,
                    hero_id=hero_id,
                    match_id=match.match_id,
                    decayed_wins=ph_wins,
                    decayed_games=ph_games,
                    last_update_time=match_start_time,
                )
            )

            prev_hero_state = await history_repo.get_hero_state_before(hero_id, match_start_time)
            hero_wins, hero_games = self._decay_and_update_state(
                prev_hero_state, match_start_ts, hero_hl, player_won_this_match
            )
            new_hero_states.append(
                HeroDecayedStateTable(
                    hero_id=hero_id,
                    match_id=match.match_id,
                    decayed_wins=hero_wins,
                    decayed_games=hero_games,
                    last_update_time=match_start_time,
                )
            )

        if new_ph_states:
            await history_repo.upsert_player_hero_decayed_states(new_ph_states)
        if new_hero_states:
            await history_repo.upsert_hero_decayed_states(new_hero_states)
        logger.debug(
            f"Upserted {len(new_ph_states)} player-hero and {len(new_hero_states)} hero states for match {match.match_id}"
        )

    def _decay_and_update_state(
        self, previous_state, match_start_ts: int, half_life_days: float, won_this_match: bool
    ) -> tuple[float, float]:
        """Generic helper to apply decay and update a win/loss state."""
        if previous_state:
            decayed_wins, decayed_games = apply_decay_to_pair(
                previous_state.decayed_wins,
                previous_state.decayed_games,
                int(previous_state.last_update_time.timestamp()),
                match_start_ts,
                half_life_days,
            )
        else:
            decayed_wins, decayed_games = 0.0, 0.0

        decayed_games += 1.0
        if won_this_match:
            decayed_wins += 1.0

        return decayed_wins, decayed_games

    async def _get_completed_match_details(self, match_id: int, session: AsyncSession) -> MatchTable:
        """Fetches match details and ensures it has a completed outcome."""
        match_repository = MatchRepository(session=session)
        matches = await match_repository.get_match_details(input_id_list=[match_id], relationship_fields=["outcome"])

        if not matches:
            raise ValueError(f"Match {match_id} cannot be found in the database.")

        match = matches[0]
        if not match.outcome or match.outcome.radiant_win is None:
            raise ValueError(f"Match outcome for {match_id} is incomplete or not found.")

        return match
