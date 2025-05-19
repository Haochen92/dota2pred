import pandas as pd
from typing import Dict, Any, List, Coroutine, Optional
from dota_oracle.utils import get_logger, get_outcome_as_group
from dota_oracle.data_repository.history_repository import HistoryRepository
from datetime import datetime

logger = get_logger(__name__)

class PlayerHeroFeaturesProcessor:
    def __init__(self, history_repo: HistoryRepository, max_history_length: int=20):
        self.max_history_length = max_history_length
        self.history_repo = history_repo
        
    async def create_player_hero_features(
        self, 
        df: pd.DataFrame,
        before_timestamp: Optional[datetime] = None,
        after_timestamp: Optional[datetime] = None,
        history_limit: Optional[int] = None
    ) -> pd.DataFrame:
        
        all_match_features: List[Dict[str, Any]] = []
        player_slots = list(range(5)) + list(range(128, 133))
        match_records = df.to_dict('records')
        
        for match in match_records:
            match_id = match.get('match_id')
            try:                
                tasks_dict: Dict[str, Coroutine[Any, Any, float]] = {}
                
                for i in player_slots:
                    account_id = match[f'slot_{i}_account_id']
                    hero_id = match[f'slot_{i}_hero_id']
                    feature_key = f'player_hero_{i}_win_rate'
                    start_time = match['start_time']
                    
                    if pd.isna(account_id) or pd.isna(hero_id) or pd.isna(start_time):
                        raise ValueError(
                            f"Match {match_id}, Slot {i}: Missing account_id ({account_id})"
                            f"or hero_id ({hero_id})."
                            f"or start_time ({start_time})" 
                            f"Failing this match."
                        )
                    effective_before = before_timestamp if before_timestamp is not None else start_time
                        
                    tasks_dict[feature_key] = self._calculate_win_rate(account_id, hero_id, effective_before)
                
                outcome_dict: Dict[str, float] = await get_outcome_as_group(tasks_dict)
                feature_row_with_id = {'match_id': match_id, **outcome_dict}
                all_match_features.append(feature_row_with_id)
            
            except ValueError as ve:
                print(f"Skipping match {match_id} due to missing player data: {ve}")
                continue
            except Exception as e:
                logger.error(f"Error for match {match_id}: {e}")
                continue

        return pd.DataFrame(all_match_features)

    async def _calculate_win_rate(self, account_id: int, hero_id: int, before: datetime) -> float:
        
        history: List[bool] = await self.history_repo.get_player_hero_win_history(account_id, hero_id, before)
        if not history:
            return 0.5
        
        wins = sum(1 for outcome in history if outcome is True)
        total_games = len(history)
        win_rate = wins / total_games if total_games > 0 else 0.5
        return win_rate
    


    
    
    
