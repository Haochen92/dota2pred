from typing import List, Optional
from dota_oracle_common.utils import get_logger
from dota_oracle_common.utils.async_utils import TaskRunner
from dota_oracle_common.models.utils import AsyncTask
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
        after_timestamp: Optional[datetime] = None,
        history_limit: Optional[int] = None,
    ) -> List[PlayerHeroFeatureTable]:

        player_hero_features_list: List[PlayerHeroFeatureTable] = []
        player_slots = list(range(5)) + list(range(128, 133))

        for instance in match_instances:
            match_id = instance.match_id
            try:
                # Create AsyncTask objects for all player-hero combinations
                player_hero_tasks = []

                for i in player_slots:
                    account_id = getattr(instance, f"slot_{i}_account_id")
                    hero_id = getattr(instance, f"slot_{i}_hero_id")
                    feature_key = f"player_hero_{i}_win_rate"
                    start_time = instance.start_time

                    if not account_id or not hero_id or not start_time:
                        raise ValueError(
                            f"Match {match_id}, Slot {i}: Missing account_id ({account_id}) "
                            f"or hero_id ({hero_id}) or start_time ({start_time}). "
                            f"Failing this match."
                        )

                    effective_before = before_timestamp if before_timestamp is not None else start_time

                    # Create task for this player-hero combination
                    task = AsyncTask(
                        key=feature_key, coro=self._calculate_win_rate(session, account_id, hero_id, effective_before)
                    )
                    player_hero_tasks.append(task)

                # Execute all player-hero tasks concurrently for this match
                results = await TaskRunner.run_concurrently(player_hero_tasks)

                # Extract results from TaskResult objects
                outcome_dict = {}
                for task_result in results:
                    try:
                        outcome_dict[task_result.key] = task_result.get_result()
                    except Exception as e:
                        logger.warning(f"Task {task_result.key} failed for match {match_id}: {e}")
                        outcome_dict[task_result.key] = 0.5  # Default fallback

                # Create single feature row for this match with all player-hero win rates
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
