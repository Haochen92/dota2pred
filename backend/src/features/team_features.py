import pandas as pd
from typing import Dict, List, Any, Optional
import asyncio 

from repositories.histories_repository import HistoryRepository 
from src.utils.set_logging import get_logger 

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
            before_timestamp: Optional[int] = None,
            after_timestamp: Optional[int] = 0,
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

            # Basic check for necessary info
            if not match_id or not radiant_team or not dire_team:
                logger.warning(f"Skipping match {match_id or 'N/A'}: missing ID or team names.")
                all_match_features.append({'match_id': match_id, 'radiant_win_rate': 0.5, 'dire_win_rate': 0.5, 'radiant_dire_matchup': 0.5})
                continue

            match_result: Dict[str, Any] = {'match_id': match_id}
            tasks = {} 

            try:
                # --- Prepare Concurrent Tasks ---
                # Radiant Win Rate Task
                tasks['rad_wr'] = asyncio.create_task(
                    self._calculate_team_win_rate(radiant_team, before=effective_before, after=after_timestamp, limit=history_limit)
                )
                # Dire Win Rate Task
                tasks['dire_wr'] = asyncio.create_task(
                    self._calculate_team_win_rate(dire_team, before=effective_before, after=after_timestamp, limit=history_limit)
                )
                
                tasks['matchup'] = asyncio.create_task(
                    self._calculate_matchup_win_rate(radiant_team, dire_team, before=effective_before, after=after_timestamp, limit=history_limit)
                )

                if tasks:
                    task_keys = list(tasks.keys())
                    task_values = list(tasks.values())
                    results = await asyncio.gather(*task_values, return_exceptions=True)
                else:
                    results = [] 
                    
                results_dict = {}
                for i, result in enumerate(results):
                    key = task_keys[i]
                    if isinstance(result, Exception):
                        logger.error(f"Error calculating '{key}' for match {match_id}: {result}")
                        results_dict[key] = 0.5 # Default on error
                    else:
                        results_dict[key] = result

                match_result['radiant_win_rate'] = results_dict.get('rad_wr', 0.5)
                match_result['dire_win_rate'] = results_dict.get('dire_wr', 0.5)
                match_result['radiant_dire_matchup'] = results_dict.get('matchup', 0.5)

            except KeyError as e:
                 logger.error(f"Missing expected key in match data for match {match_id}: {e}", exc_info=True)
                 match_result.update({'radiant_win_rate': 0.5, 'dire_win_rate': 0.5, 'radiant_dire_matchup': 0.5})
            except Exception as e:
                 logger.error(f"Unexpected error processing match {match_id}: {e}", exc_info=True)
                 match_result.update({'radiant_win_rate': 0.5, 'dire_win_rate': 0.5, 'radiant_dire_matchup': 0.5})


            all_match_features.append(match_result)

        logger.info("Finished calculating team features.")
        if not all_match_features:
            return pd.DataFrame()

        return pd.DataFrame(all_match_features)


    async def _calculate_team_win_rate(self,
                                       team_name: Optional[str],
                                       before: Optional[int] = None,
                                       after: Optional[int] = 0,
                                       limit: Optional[int] = None
                                    ) -> float:
        """Calculates win rate for a single team using the history repository."""
        if not team_name:
            return 0.5

        # Call the injected repository's method, passing filters
        # Assumes repo method handles limit defaulting if None is passed
        team_win_history: List[bool] = await self.history_repo.get_team_win_history(
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
                                        before: Optional[int] = None,
                                        after: Optional[int] = 0,
                                        limit: Optional[int] = None
                                        ) -> float:
        """Calculates the head-to-head win rate for team_name against opponent_name."""
        # Input validation
        if not team_name or not opponent_name:
            logger.warning(f"Invalid input for matchup calc: team={team_name}, opp={opponent_name}")
            return 0.5

        # Standardize team order for repository lookup
        team1, team2 = sorted([team_name, opponent_name])

        # Call the injected repository's method, passing filters
        # Assumes repo method handles limit defaulting if None is passed
        # History is returned from team1's perspective (True if team1 won)
        team1_win_history: List[bool] = await self.history_repo.get_team_matchup_win_history(
            team1_name=team1,
            team2_name=team2,
            before=before,
            after=after,
            limit=limit
        )

        if not team1_win_history:
            # logger.debug(f"No matchup history found for {team1} vs {team2}. Returning default.")
            return 0.5

        total_matchups = len(team1_win_history)
        target_team_wins = 0

        # Calculate wins for the original team_name based on team1's results
        if team_name == team1:
            target_team_wins = sum(1 for win in team1_win_history if win is True)
        else: # target team must be team2
            target_team_wins = sum(1 for win in team1_win_history if win is False)

        win_rate = target_team_wins / total_matchups
        return win_rate