import pandas as pd
from typing import Dict, Any, List
from utils.set_logging import get_logger
from data_repository.history_repository import HistoryRepository
import asyncio

logger = get_logger(__name__)

class PlayerHeroFeaturesProcessor:
    def __init__(self, history_repo: HistoryRepository, max_history_length: int=20):
        self.max_history_length = max_history_length
        self.history_repo = history_repo
        
    async def create_player_hero_features(self, df: pd.DataFrame) -> pd.DataFrame:
        
        features = []
        
        for _, match in df.iterrows():
            match_id = match['match_id']
            match_result: Dict[str, Any] = {'match_id':match_id}
            
            tasks: Dict[str, asyncio.Task] = {}
            
            for i in list(range(5)) + list(range(128, 133)):
                account_id = match[f'slot_{i}_account_id']
                hero_id = match[f'slot_{i}_hero_id']
                feature_key = f'player_hero_{i}_win_rate'
                
                co_routine = self._calculate_win_rate(account_id, hero_id)
                tasks[feature_key] = asyncio.create_task(co_routine)
            
            if tasks:
                task_values = list(tasks.values())
                results = await asyncio.gather(*task_values, return_exceptions=True)
                task_keys = list(tasks.keys())
                
                for i, result in enumerate(results):
                    feature_key = task_keys[i]
                    match_result[feature_key] = result
            # Append complete match result with all player win rates
            features.append(match_result)

        return pd.DataFrame(features)

    async def _calculate_win_rate(self, account_id: int, hero_id: int) -> float:
        if not account_id or not hero_id:
            logger.debug(f"Invalid account_id ({account_id}) or hero_id ({hero_id}) received. Returning default win rate.")
            return 0.5 
        
        history: List[bool] = await self.history_repo.fetch_player_hero_history(account_id, hero_id)
        if not history:
            return 0.5
        
        wins = sum(1 for outcome in history if outcome is True)
        total_games = len(history)
        win_rate = wins / total_games if total_games > 0 else 0.5
        return win_rate
    


    
    
    
