from typing import List, Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from dota_oracle_common.models.features import TeamFeaturesTable
from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.repositories.history_repository import HistoryRepository
from dota_oracle_common.utils import get_logger
from dota_oracle_common.utils.time_utils import get_current_utc_iso_timestamp

from .decay_utils import apply_decay_to_pair

logger = get_logger(__name__)


class TeamFeatureCreator:
    def __init__(
        self,
        prior_mean: float = 0.5,
        prior_count: float = 20.0,
        half_life_days: float = 45.0,
    ) -> None:
        self.prior_mean = prior_mean
        self.prior_count = prior_count
        self.half_life_days = half_life_days

    async def create_team_features(
        self,
        db_session: AsyncSession,
        match_instances: List[MatchTable],
        before_timestamp: Optional[datetime] = None,
        after_timestamp: Optional[datetime] = None,
        history_limit: Optional[int] = None,
    ) -> List[TeamFeaturesTable]:

        if not match_instances:
            logger.warning("No match instances for team feature processing")
            return []

        all_match_features = []
        logger.info(f"Calculating team features for {len(match_instances)} matches...")

        for instance in match_instances:
            try:
                match_id = instance.match_id
                radiant_team_id = instance.radiant_team_id
                dire_team_id = instance.dire_team_id
                current_match_start = instance.start_time

                if before_timestamp:
                    effective_before = before_timestamp
                elif current_match_start:
                    effective_before = current_match_start
                else:
                    effective_before = get_current_utc_iso_timestamp()

                radiant_win_rate = await self._calculate_team_win_rate(
                    db_session,
                    radiant_team_id,
                    before=effective_before,
                    after=after_timestamp,
                    limit=history_limit,
                )

                dire_win_rate = await self._calculate_team_win_rate(
                    db_session, dire_team_id, before=effective_before, after=after_timestamp, limit=history_limit
                )

                radiant_dire_matchup = await self._calculate_matchup_win_rate(
                    db_session,
                    radiant_team_id,
                    dire_team_id,
                    before=effective_before,
                    after=after_timestamp,
                    limit=history_limit,
                )

                # Create the feature row
                team_features_row = TeamFeaturesTable(
                    match_id=match_id,
                    radiant_win_rate=radiant_win_rate,
                    dire_win_rate=dire_win_rate,
                    radiant_dire_matchup=radiant_dire_matchup,
                )
                all_match_features.append(team_features_row)

            except Exception as e:
                logger.error(
                    f"Unexpected error processing match {getattr(instance, 'match_id', 'unknown')}: {e}", exc_info=True
                )
                raise e

        logger.info(f"Created {len(all_match_features)} / {len(match_instances)} team features")
        return all_match_features

    async def _calculate_team_win_rate(
        self,
        session: AsyncSession,
        team_id: Optional[int],
        before: datetime,
        after: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> float:
        """Calculates time-decayed win rate for a single team.

        Uses the most recent decayed state prior to `before`, advances it to `before`
        using exponential decay with half-life `self.half_life_days`, and applies
        Bayesian smoothing with prior (`self.prior_mean`, `self.prior_count`).
        """
        try:
            if not team_id:  # team might be new or unregistered
                return self.prior_mean

            history_repo = HistoryRepository(session=session)
            state = await history_repo.get_team_state_before_by_id(team_id, before)

            if not state:
                return self.prior_mean

            weighted_wins, weighted_games = apply_decay_to_pair(
                state.decayed_wins,
                state.decayed_games,
                int(state.last_update_time.timestamp()),
                int(before.timestamp()),
                self.half_life_days,
            )

            denom = weighted_games + self.prior_count
            if denom <= 0:
                return self.prior_mean
            return (weighted_wins + self.prior_count * self.prior_mean) / denom

        except Exception as e:
            logger.error(f"Error calculating win rate for team_id '{team_id}': {e}", exc_info=True)
            raise

    async def _calculate_matchup_win_rate(
        self,
        session: AsyncSession,
        team_id: Optional[int],
        opponent_id: Optional[int],
        before: datetime,
        after: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> float:
        """Calculates time-decayed head-to-head win rate for `team_name` vs `opponent_name`.

        Reads the latest matchup decayed state prior to `before`, advances it to
        `before` using exponential decay, then applies smoothing with the team prior.
        """
        try:
            # Input validation
            if not team_id or not opponent_id:
                logger.warning(f"Missing team id for matchup calc: team_id={team_id}, opp_id={opponent_id}")
                return self.prior_mean

            history_repo = HistoryRepository(session=session)

            # Standardize order for repository lookup
            team1_id, team2_id = sorted([team_id, opponent_id])
            state = await history_repo.get_team_matchup_state_before_by_id(team1_id, team2_id, before)

            if not state:
                return self.prior_mean

            # From team1's perspective
            w_t1_wins, w_games = apply_decay_to_pair(
                state.decayed_t1_wins,
                state.decayed_games,
                int(state.last_update_time.timestamp()),
                int(before.timestamp()),
                self.half_life_days,
            )

            # Team1 perspective: if requesting team is team1_id, use t1 wins; otherwise invert
            weighted_wins = w_t1_wins if team_id == team1_id else (w_games - w_t1_wins)

            denom = w_games + self.prior_count
            if denom <= 0:
                return self.prior_mean
            return (weighted_wins + self.prior_count * self.prior_mean) / denom

        except Exception as e:
            logger.error(
                f"Error calculating matchup rate for team_id='{team_id}' vs opp_id='{opponent_id}': {e}",
                exc_info=True,
            )
            raise
