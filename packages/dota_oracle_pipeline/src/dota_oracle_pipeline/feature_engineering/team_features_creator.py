from typing import List, Optional
from dota_oracle_common.repositories.history_repository import HistoryRepository
from dota_oracle_common.utils import get_logger
from dota_oracle_common.utils.time_utils import get_current_utc_iso_timestamp
from datetime import datetime
from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.models.features import TeamFeaturesTable
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class TeamFeatureCreator:

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
                radiant_team = instance.radiant_name
                dire_team = instance.dire_name
                current_match_start = instance.start_time

                if before_timestamp:
                    effective_before = before_timestamp
                elif current_match_start:
                    effective_before = current_match_start
                else:
                    effective_before = get_current_utc_iso_timestamp()

                radiant_win_rate = await self._calculate_team_win_rate(
                    db_session,
                    radiant_team,
                    before=effective_before,
                    after=after_timestamp,
                    limit=history_limit,
                )

                dire_win_rate = await self._calculate_team_win_rate(
                    db_session, dire_team, before=effective_before, after=after_timestamp, limit=history_limit
                )

                radiant_dire_matchup = await self._calculate_matchup_win_rate(
                    db_session,
                    radiant_team,
                    dire_team,
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
        team_name: Optional[str],
        before: datetime,
        after: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> float:
        """Calculates win rate for a single team using a fresh repository instance."""
        try:
            if not team_name:  # team might be new or unregistered
                return 0.5

            # Create fresh repository instance with current session
            history_repo = HistoryRepository(session=session)

            # Call the repository's method, passing filters
            team_win_history: List[bool] = await history_repo.get_team_history(
                team_name=team_name, before=before, after=after, limit=limit
            )

            if not team_win_history:
                return 0.5

            wins = sum(1 for outcome in team_win_history if outcome is True)
            total_games = len(team_win_history)

            return wins / total_games if total_games > 0 else 0.5

        except Exception as e:
            logger.error(f"Error calculating win rate for team '{team_name}': {e}", exc_info=True)
            raise

    async def _calculate_matchup_win_rate(
        self,
        session: AsyncSession,
        team_name: Optional[str],
        opponent_name: Optional[str],
        before: datetime,
        after: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> float:
        """Calculates the head-to-head win rate for team_name against opponent_name."""
        try:
            # Input validation
            if not team_name or not opponent_name:
                logger.warning(f"Missing team name for matchup calc: team={team_name}, opp={opponent_name}")
                return 0.5

            # Create fresh repository instance with current session
            history_repo = HistoryRepository(session=session)

            # Standardize team order for repository lookup
            team1, team2 = sorted([team_name, opponent_name])

            team1_win_history: List[bool] = await history_repo.get_team_matchup_history(
                team_one=team1, team_two=team2, before=before, after=after, limit=limit
            )

            if not team1_win_history:
                return 0.5

            total_matchups = len(team1_win_history)
            target_team_wins = 0

            if team_name == team1:
                target_team_wins = sum(1 for win in team1_win_history if win is True)
            else:
                target_team_wins = sum(1 for win in team1_win_history if win is False)

            win_rate = target_team_wins / total_matchups
            return win_rate

        except Exception as e:
            logger.error(f"Error calculating matchup rate for '{team_name}' vs '{opponent_name}': {e}", exc_info=True)
            raise
