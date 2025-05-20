from typing import Dict, List, Any, Optional, Coroutine
from dota_oracle.data_repository.history_repository import HistoryRepository 
from dota_oracle.utils import get_logger, get_outcome_as_group
from dota_oracle.utils.time_utils import get_current_utc_iso_timestamp
from datetime import datetime
from dota_oracle.data_repository.schemas import MatchTable, TeamFeaturesTable

logger = get_logger(__name__) 

class TeamFeatureProcessor:
    def __init__(self, history_repository: HistoryRepository):
        """
        Calculates team-level features based on historical data.

        Args:
            history_repository: An instance of HistoryRepository to fetch history data.
        """
        self.history_repo = history_repository

    async def create_team_features(
            self,
            match_instances: List[MatchTable],
            before_timestamp: Optional[datetime] = None,
            after_timestamp: Optional[datetime] = None,
            history_limit: Optional[int] = None
        ) -> List[TeamFeaturesTable]:
        
        if not match_instances:
            logger.warning(f"No match instances for team feature processing")
            return []

        all_match_features = []
        logger.info(f"Calculating team features for {len(match_instances)} matches...")

        for instance in match_instances:
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


            tasks_dict: Dict[str, Coroutine[Any, Any, float]] = {
                'radiant_win_rate': self._calculate_team_win_rate(radiant_team, before=effective_before),
                'dire_win_rate': self._calculate_team_win_rate(dire_team, before=effective_before),
                'radiant_dire_matchup': self._calculate_matchup_win_rate(radiant_team, dire_team, before=effective_before)
            }

            try:
                outcome_dict: Dict[str, float] = await get_outcome_as_group(tasks_dict)
                team_features_row = TeamFeaturesTable(
                    match_id=instance.match_id,
                    radiant_win_rate=outcome_dict['radiant_win_rate'],
                    dire_win_rate=outcome_dict['dire_win_rate'],
                    radiant_dire_matchup=outcome_dict['radiant_dire_matchup']
                )
                all_match_features.append(team_features_row)
            except Exception as e:
                 logger.error(f"Unexpected error processing match {match_id}: {e}", exc_info=True)
                 continue


        logger.info(f"Created {len(all_match_features)} / {len(match_instances)} matches features")

        return all_match_features


    async def _calculate_team_win_rate(self,
                                       team_name: Optional[str],
                                       before: datetime,
                                       after: Optional[datetime] = None,
                                       limit: Optional[int] = None
                                    ) -> float:
        """Calculates win rate for a single team using the history repository."""
        if not team_name: # team might be new or unregistered
            return 0.5

        # Call the injected repository's method, passing filters
        # Assumes repo method handles limit defaulting if None is passed
        team_win_history: List[bool] = await self.history_repo.get_team_history(
            team_name=team_name,
            before=before,
            after=after,
            limit=limit
        )

        if not team_win_history:
            return 0.5

        wins = sum(1 for outcome in team_win_history if outcome is True)
        total_games = len(team_win_history)

        return wins / total_games if total_games > 0 else 0.5


    async def _calculate_matchup_win_rate(self,
                                        team_name: Optional[str], 
                                        opponent_name: Optional[str],
                                        before: datetime,
                                        after: Optional[datetime] = None,
                                        limit: Optional[int] = None
                                        ) -> float:
        """Calculates the head-to-head win rate for team_name against opponent_name."""
        # Input validation
        if not team_name or not opponent_name:
            logger.warning(f"Missing team name for matchup calc: team={team_name}, opp={opponent_name}")
            return 0.5

        # Standardize team order for repository lookup
        team1, team2 = sorted([team_name, opponent_name])

        team1_win_history: List[bool] = await self.history_repo.get_team_matchup_history(
            team_one=team1,
            team_two=team2,
            before=before,
            after=after,
            limit=limit
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