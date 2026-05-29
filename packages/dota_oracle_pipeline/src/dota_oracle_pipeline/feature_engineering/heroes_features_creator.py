from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from dota_oracle_common.models.features import HeroFeaturesTable
from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.repositories.history_repository import HistoryRepository
from dota_oracle_common.utils import get_logger

from .decay_utils import apply_decay_to_pair

logger = get_logger(__name__)


class HeroesFeatureCreator:
    def __init__(
        self,
        prior_mean: float = 0.5,
        prior_count: float = 50.0,
        half_life_days: float = 60.0,
    ) -> None:
        self.prior_mean = prior_mean
        self.prior_count = prior_count
        self.half_life_days = half_life_days

    async def create_hero_features(
        self, session: AsyncSession, match_instances: List[MatchTable]
    ) -> List[HeroFeaturesTable]:
        """Create per-slot hero win-rate features using time-decayed global hero performance.

        For each drafted hero in a match, this computes a decayed win rate:
            (decayed_wins + prior_count * prior_mean) / (decayed_games + prior_count)
        where decayed values are advanced from their last update time up to the
        match start using an exponential half-life.
        """

        if not match_instances:
            logger.warning("No match instances for hero feature processing")
            return []

        history_repo = HistoryRepository(session=session)
        hero_features: List[HeroFeaturesTable] = []

        for instance in match_instances:
            try:
                start_time = instance.start_time
                if not start_time:
                    raise ValueError(f"Match {instance.match_id} missing start_time")

                outcome_fields = {}

                slot_indices = list(range(5)) + list(range(128, 133))
                for slot in slot_indices:
                    hero_id = getattr(instance, f"slot_{slot}_hero_id", None)
                    field_key = f"hero_{slot}_win_rate"

                    if hero_id is None:
                        outcome_fields[field_key] = self.prior_mean
                        continue

                    state = await history_repo.get_hero_state_before(hero_id, start_time)
                    if not state:
                        outcome_fields[field_key] = self.prior_mean
                        continue

                    weighted_wins, weighted_games = apply_decay_to_pair(
                        state.decayed_wins,
                        state.decayed_games,
                        int(state.last_update_time.timestamp()),
                        int(start_time.timestamp()),
                        self.half_life_days,
                    )

                    denom = weighted_games + self.prior_count
                    if denom <= 0:
                        outcome_fields[field_key] = self.prior_mean
                    else:
                        outcome_fields[field_key] = (weighted_wins + self.prior_count * self.prior_mean) / denom

                hero_features.append(
                    HeroFeaturesTable(
                        match_id=instance.match_id,
                        **outcome_fields,
                    )
                )
            except Exception as e:
                logger.error(
                    f"Error creating hero features for match {getattr(instance, 'match_id', 'unknown')}: {e}",
                    exc_info=True,
                )
                continue

        if len(hero_features) < len(match_instances):
            failed = len(match_instances) - len(hero_features)
            logger.warning(f"Hero feature engineering: {failed}/{len(match_instances)} matches failed")

        logger.info(f"Created {len(hero_features)} hero features")
        return hero_features
