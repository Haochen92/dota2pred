from typing import Dict, Any, List, Coroutine, Optional
from dota_oracle.utils import get_logger, get_outcome_as_group
from dota_oracle.data_repository.history_repository import HistoryRepository
from dota_oracle.models.match import MatchTable
from dota_oracle.models.features import PlayerHeroFeatureTable
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

logger = get_logger(__name__)

class PlayerHeroFeaturesProcessor:
    def __init__(self, db_engine: AsyncEngine, max_history_length: int=20):
        self.max_history_length = max_history_length
        self.engine = db_engine

        
    async def create_player_hero_features(
        self, 
        match_instances: List[MatchTable],
        before_timestamp: Optional[datetime] = None,
        after_timestamp: Optional[datetime] = None,
        history_limit: Optional[int] = None
    ) -> List[PlayerHeroFeatureTable]:
        
        player_hero_features_list: List[PlayerHeroFeatureTable] = []
        player_slots = list(range(5)) + list(range(128, 133))
        
        for instance in match_instances:
            match_id = instance.match_id
            try:
                # Create one session per match
                async with AsyncSession(self.engine) as session:
                    tasks_dict: Dict[str, Coroutine[Any, Any, float]] = {}
                    
                    for i in player_slots:
                        account_id = getattr(instance, f'slot_{i}_account_id')
                        hero_id = getattr(instance, f'slot_{i}_hero_id')
                        feature_key = f'player_hero_{i}_win_rate'
                        start_time = instance.start_time
                        
                        if not account_id or not hero_id or not start_time:
                            raise ValueError(
                                f"Match {match_id}, Slot {i}: Missing account_id ({account_id})"
                                f"or hero_id ({hero_id})."
                                f"or start_time ({start_time})" 
                                f"Failing this match."
                            )
                        effective_before = before_timestamp if before_timestamp is not None else start_time
                            
                        # Pass the shared session to each calculation
                        tasks_dict[feature_key] = self._calculate_win_rate(
                            session, account_id, hero_id, effective_before
                        )
                    
                    outcome_dict: Dict[str, float] = await get_outcome_as_group(tasks_dict)
                    feature_row_with_id = PlayerHeroFeatureTable(
                        match_id=instance.match_id,
                        **outcome_dict
                    )
                    player_hero_features_list.append(feature_row_with_id)
            
            except ValueError as ve:
                logger.error(f"Skipping match {match_id} due to missing player data: {ve}")
                continue
            except Exception as e:
                logger.error(f"Error for match {match_id}: {e}")
                continue

        return player_hero_features_list

    async def _calculate_win_rate(
        self, 
        session: AsyncSession, 
        account_id: int, 
        hero_id: int, 
        before: datetime
    ) -> float:
        # Use the provided session without creating a new transaction
        history_repository = HistoryRepository(session=session)
        history = await history_repository.get_player_hero_win_history(account_id, hero_id, before)
        
        if not history:
            return 0.5
        
        wins = sum(1 for outcome in history if outcome is True)
        total_games = len(history)
        win_rate = wins / total_games if total_games > 0 else 0.5
        return win_rate