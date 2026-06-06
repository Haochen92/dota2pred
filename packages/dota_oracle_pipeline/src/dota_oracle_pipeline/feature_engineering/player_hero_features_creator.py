from typing import List
from dota_oracle_pipeline.feature_engineering.decay_utils import apply_decay_to_pair
from dota_oracle_common.utils import get_logger
from dota_oracle_common.repositories.history_repository import HistoryRepository
from dota_oracle_common.models.features import PlayerHeroFeatureTable
from dota_oracle_common.models.match import MatchTable
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class PlayerHeroFeaturesCreator:
    def __init__(
        self,
        player_prior_count: float = 8.0,
        player_half_life_days: float = 30.0,
        hero_prior_mean: float = 0.5,
        hero_prior_count: float = 50.0,
        hero_half_life_days: float = 60.0,
    ):
        self.player_prior_count = player_prior_count
        self.player_half_life_days = player_half_life_days
        self.hero_prior_mean = hero_prior_mean
        self.hero_prior_count = hero_prior_count
        self.hero_half_life_days = hero_half_life_days

    async def create_player_hero_features(
        self,
        session: AsyncSession,
        match_instances: List[MatchTable],
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

                    hero_prior = await self._calculate_hero_prior(session, hero_id, start_time)

                    win_rate = await self._calculate_decayed_win_rate(
                        session, account_id, hero_id, hero_prior, start_time
                    )

                    outcome_dict[feature_key] = win_rate
                feature_row = PlayerHeroFeatureTable(match_id=instance.match_id, **outcome_dict)
                player_hero_features_list.append(feature_row)

            except ValueError as ve:
                logger.error(f"Skipping match {match_id} due to missing player data: {ve}")
                continue
            except Exception as e:
                logger.error(f"Error processing match {match_id}: {e}", exc_info=True)
                continue

        if len(player_hero_features_list) < len(match_instances):
            failed = len(match_instances) - len(player_hero_features_list)
            logger.warning(f"Player-hero feature engineering: {failed}/{len(match_instances)} matches failed")

        logger.info(f"Created {len(player_hero_features_list)} player-hero feature rows")
        return player_hero_features_list

    async def _calculate_decayed_win_rate(
        self, session: AsyncSession, account_id: int, hero_id: int, hero_prior: float, before: datetime
    ) -> float:
        """Calculate decayed win rate for a specific player-hero combination."""
        try:
            history_repository = HistoryRepository(session=session)
            history_state = await history_repository.get_player_hero_state_before(account_id, hero_id, before)

            if not history_state:
                return hero_prior

            decayed_wins, decayed_games, last_update_time = (
                history_state.decayed_wins,
                history_state.decayed_games,
                history_state.last_update_time,
            )

            weighted_wins, weighted_games = apply_decay_to_pair(
                decayed_wins,
                decayed_games,
                int(last_update_time.timestamp()),
                int(before.timestamp()),
                self.player_half_life_days,
            )

            denominator = weighted_games + self.player_prior_count
            if denominator <= 0:
                return hero_prior
            win_rate = (weighted_wins + self.player_prior_count * hero_prior) / denominator
            return win_rate

        except Exception as e:
            logger.error(
                f"Error calculating win rate for account_id {account_id}, hero_id {hero_id}: {e}", exc_info=True
            )
            raise

    async def _calculate_hero_prior(self, session: AsyncSession, hero_id: int, before: datetime) -> float:
        """Calculate decayed hero prior for a specific player-hero combination."""
        try:
            history_repository = HistoryRepository(session=session)

            history_state = await history_repository.get_hero_state_before(hero_id, before)

            if not history_state:
                return self.hero_prior_mean

            decayed_wins, decayed_games, last_update_time = (
                history_state.decayed_wins,
                history_state.decayed_games,
                history_state.last_update_time,
            )

            weighted_wins, weighted_games = apply_decay_to_pair(
                decayed_wins,
                decayed_games,
                int(last_update_time.timestamp()),
                int(before.timestamp()),
                self.hero_half_life_days,
            )

            denominator = weighted_games + self.hero_prior_count
            if denominator <= 0:
                return self.hero_prior_mean

            win_rate = (weighted_wins + self.hero_prior_count * self.hero_prior_mean) / denominator
            return win_rate

        except Exception as e:
            logger.error(f"Error calculating win rate for account_id , hero_id {hero_id}: {e}", exc_info=True)
            raise
