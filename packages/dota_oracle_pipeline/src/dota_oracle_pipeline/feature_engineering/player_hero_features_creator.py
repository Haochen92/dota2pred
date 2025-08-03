from typing import List, Optional
from dota_oracle_common.utils import get_logger
from dota_oracle_common.repositories.history_repository import HistoryRepository
from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.models.features import PlayerHeroFeatureTable
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class PlayerHeroFeaturesCreator:
    def __init__(self, max_history_length: int = 20):
        self.max_history_length = max_history_length

    async def create_player_hero_features(
        self,
        session: AsyncSession,
        match_instances: List[MatchTable],
        before_timestamp: Optional[datetime] = None,
    ) -> List[PlayerHeroFeatureTable]:

        player_hero_features_list: List[PlayerHeroFeatureTable] = []
        player_slots = list(range(5)) + list(range(128, 133))

        for instance in match_instances:
            match_id = instance.match_id
            try:
                outcome_dict = {}

                for i in player_slots:
                    account_id = getattr(instance, f"slot_{i}_account_id")
                    hero_id = getattr(instance, f"slot_{i}_hero_id")
                    feature_key = f"player_hero_{i}_win_rate"
                    start_time = instance.start_time

                    if not account_id or not hero_id or not start_time:
                        raise ValueError(f"Match {match_id}, Slot {i}: Missing required data.")

                    effective_before = before_timestamp if before_timestamp is not None else start_time

                    win_rate = await self._calculate_win_rate(session, account_id, hero_id, effective_before)

                    outcome_dict[feature_key] = win_rate
                feature_row = PlayerHeroFeatureTable(match_id=instance.match_id, **outcome_dict)
                player_hero_features_list.append(feature_row)

            except ValueError as ve:
                logger.error(f"Skipping match {match_id} due to missing player data: {ve}")
                continue
            except Exception as e:
                logger.error(f"Error processing match {match_id}: {e}", exc_info=True)
                continue

        logger.info(f"Created {len(player_hero_features_list)} player-hero feature rows")
        return player_hero_features_list

    async def _calculate_win_rate(
        self, session: AsyncSession, account_id: int, hero_id: int, before: datetime
    ) -> float:
        """Calculate win rate for a specific player-hero combination."""
        try:
            # Create fresh repository instance with the provided session
            history_repository = HistoryRepository(session=session)

            history = await history_repository.get_player_hero_win_history(account_id, hero_id, before)

            if not history:
                return 0.5

            wins = sum(1 for outcome in history if outcome is True)
            total_games = len(history)
            win_rate = wins / total_games if total_games > 0 else 0.5

            return win_rate

        except Exception as e:
            logger.warning(f"Error calculating win rate for account_id {account_id}, hero_id {hero_id}: {e}")
            return 0.5
