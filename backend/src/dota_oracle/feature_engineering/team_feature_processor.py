import pandas as pd
from typing import Dict, List, Any, Optional, Coroutine
from dota_oracle.data_repository.history_repository import HistoryRepository 
from dota_oracle.utils import get_logger, get_outcome_as_group
from datetime import datetime

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
            df: pd.DataFrame,
            before_timestamp: Optional[datetime] = None,
            after_timestamp: Optional[datetime] = None,
            history_limit: Optional[int] = None
        ) -> pd.DataFrame:
        
        if df.empty:
            logger.info("Input DataFrame is empty. Returning empty DataFrame.")
            return pd.DataFrame()

        all_match_features = []
        logger.info(f"Calculating team features for {len(df)} matches...")

        match_records = df.to_dict('records')

        for match in match_records:
            match_id = match.get('match_id')
            radiant_team = match.get('radiant_name')
            dire_team = match.get('dire_name')

            current_match_start = match.get('start_time')
            effective_before = before_timestamp if before_timestamp is not None else current_match_start

            tasks_dict: Dict[str, Coroutine[Any, Any, float]] = {
                'radiant_win_rate': self._calculate_team_win_rate(radiant_team, before=effective_before),
                'dire_win_rate': self._calculate_team_win_rate(dire_team, before=effective_before),
                'radiant_dire_matchup': self._calculate_matchup_win_rate(radiant_team, dire_team, before=effective_before)
            }

            try:
                outcome_dict: Dict[str, float] = await get_outcome_as_group(tasks_dict)
                row_features = {'match_id': match_id, **outcome_dict}
                all_match_features.append(row_features)
            except Exception as e:
                 logger.error(f"Unexpected error processing match {match_id}: {e}", exc_info=True)
                 continue


        logger.info("Finished calculating team features.")

        return pd.DataFrame(all_match_features)


    async def _calculate_team_win_rate(self,
                                       team_name: Optional[str],
                                       before: datetime,
                                       after: Optional[datetime] = None,
                                       limit: Optional[int] = None
                                    ) -> float:
        """Calculates win rate for a single team using the history repository."""
        if not team_name:
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
                                        team_name: str, 
                                        opponent_name: str,
                                        before: datetime ,
                                        after: Optional[datetime] = None,
                                        limit: Optional[int] = None
                                        ) -> float:
        """Calculates the head-to-head win rate for team_name against opponent_name."""
        # Input validation
        if not team_name or not opponent_name:
            logger.warning(f"Invalid input for matchup calc: team={team_name}, opp={opponent_name}")
            return 0.5

        # Standardize team order for repository lookup
        team1, team2 = sorted([team_name, opponent_name])

        team1_win_history: List[bool] = await self.history_repo.get_team_matchup_history(
            team1_name=team1,
            team2_name=team2,
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