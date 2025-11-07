from dota_oracle_common.postgresql import DatabaseManager
from dota_oracle_common.utils import get_logger
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from prefect import flow

from dota_oracle_pipeline.feature_engineering.batch.hero_wr_features.decay import BatchHeroWinrateDecayFeatureGenerator
from dota_oracle_pipeline.feature_engineering.batch.player_hero_features.dynamic_prior import (
    BatchPlayerHeroDynamicPriorFeatureGenerator,
)
from dota_oracle_pipeline.feature_engineering.batch.team_features.decay import BatchTeamDecayFeatureGenerator

from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.repositories.features_repository import FeaturesRepository
from dota_oracle_common.repositories.history_repository import HistoryRepository

from dota_oracle_common.models.features import (
    TeamFeaturesTable,
    PlayerHeroFeatureTable,
    HeroFeaturesTable,
    TeamFeaturesHyperparams,
    HeroFeaturesHyperparams,
    PlayerHeroFeaturesHyperparams,
)

from dota_oracle_common.models.histories import (
    TeamDecayedStateTable,
    TeamMatchupDecayedStateTable,
    PlayerHeroDecayedStateTable,
    HeroDecayedStateTable,
)


logger = get_logger(__name__)

TEAM_FEATURES_HYPERPARAMS = TeamFeaturesHyperparams(prior_mean=0.52, prior_count=13, half_life_days=45)

HERO_FEATURES_HYPERPARAMS = HeroFeaturesHyperparams(prior_mean=0.5, prior_count=50, half_life_days=45)

PLAYER_HERO_FEATURES_HYPERPARAMS = PlayerHeroFeaturesHyperparams(
    player_prior_count=8, player_half_life_days=60, hero_prior_count=50, hero_prior_mean=0.5, hero_half_life_days=45
)


@flow(name="backfill feature engineering and decay states", retries=2, retry_delay_seconds=10)
async def backfill_all_historical_matches(limit: Optional[int] = None):
    """
    Backfills features by processing and storing each feature set (heroes, players, teams)
    sequentially to reduce memory pressure and isolate potential failures.
    """
    local_session = DatabaseManager.get_session_factory()
    async with local_session() as db_session:
        # Memory bottleneck to consider when number of matches is very large. Change batch processing to stateful generators later.
        all_historical_matches = await get_all_matches(db_session)
        sorted_matches = sorted(all_historical_matches, key=lambda x: x.start_time)
        completed_matches = filter_completed_matches(sorted_matches)

        # Commit read only session to release any DB locks
        await db_session.commit()

        if limit is not None:
            completed_matches = completed_matches[limit:]

        # --- 1. Process and Store HERO Features ---
        logger.info("--- Starting HERO feature generation and storage ---")
        hero_generator = BatchHeroWinrateDecayFeatureGenerator()
        hero_features, hero_states = hero_generator.generate(
            completed_matches,
            prior_mean=HERO_FEATURES_HYPERPARAMS.prior_mean,
            prior_count=HERO_FEATURES_HYPERPARAMS.prior_count,
            half_life_days=HERO_FEATURES_HYPERPARAMS.half_life_days,
        )
        async with db_session.begin():
            await store_features_to_db(db_session, hero_features=hero_features)
            await store_states_to_db(db_session, hero_decay_states=hero_states)
        logger.info("--- Successfully processed and stored HERO features ---")

        # --- 2. Process and Store PLAYER-HERO Features ---
        logger.info("--- Starting PLAYER-HERO feature generation and storage ---")
        player_hero_generator = BatchPlayerHeroDynamicPriorFeatureGenerator()
        player_hero_features, player_hero_states = player_hero_generator.generate(
            completed_matches,
            player_prior_count=PLAYER_HERO_FEATURES_HYPERPARAMS.player_prior_count,
            player_half_life_days=PLAYER_HERO_FEATURES_HYPERPARAMS.player_half_life_days,
            hero_prior_count=PLAYER_HERO_FEATURES_HYPERPARAMS.hero_prior_count,
            hero_prior_mean=PLAYER_HERO_FEATURES_HYPERPARAMS.hero_prior_mean,
            hero_half_life_days=PLAYER_HERO_FEATURES_HYPERPARAMS.hero_half_life_days,
        )
        async with db_session.begin():
            await store_features_to_db(db_session, player_hero_features=player_hero_features)
            await store_states_to_db(db_session, player_hero_decay_states=player_hero_states)
        logger.info("--- Successfully processed and stored PLAYER-HERO features ---")

        # --- 3. Process and Store TEAM Features ---
        logger.info("--- Starting TEAM feature generation and storage ---")
        team_generator = BatchTeamDecayFeatureGenerator()
        team_features, team_states, team_matchup_states = team_generator.generate(
            completed_matches,
            prior_mean=TEAM_FEATURES_HYPERPARAMS.prior_mean,
            prior_count=TEAM_FEATURES_HYPERPARAMS.prior_count,
            half_life_days=TEAM_FEATURES_HYPERPARAMS.half_life_days,
        )
        async with db_session.begin():
            await store_features_to_db(db_session, team_features=team_features)
            await store_states_to_db(
                db_session, team_decay_states=team_states, team_matchup_decay_states=team_matchup_states
            )
        logger.info("--- Successfully processed and stored TEAM features ---")


async def store_features_to_db(
    db_session: AsyncSession,
    team_features: Optional[List[TeamFeaturesTable]] = None,
    hero_features: Optional[List[HeroFeaturesTable]] = None,
    player_hero_features: Optional[List[PlayerHeroFeatureTable]] = None,
):
    features_repo = FeaturesRepository(db_session)
    if team_features:
        await features_repo.store_features(team_features, TeamFeaturesTable)
        logger.info(f"Stored team features: {len(team_features)} records")
    if hero_features:
        await features_repo.store_features(hero_features, HeroFeaturesTable)
        logger.info(f"Stored hero features: {len(hero_features)} records")
    if player_hero_features:
        await features_repo.store_features(player_hero_features, PlayerHeroFeatureTable)
        logger.info(f"Stored player-hero features: {len(player_hero_features)} records")


async def store_states_to_db(
    db_session: AsyncSession,
    hero_decay_states: Optional[List[HeroDecayedStateTable]] = None,
    player_hero_decay_states: Optional[List[PlayerHeroDecayedStateTable]] = None,
    team_decay_states: Optional[List[TeamDecayedStateTable]] = None,
    team_matchup_decay_states: Optional[List[TeamMatchupDecayedStateTable]] = None,
):
    history_repo = HistoryRepository(db_session)
    if hero_decay_states:
        await history_repo.upsert_hero_decayed_states(hero_decay_states)
        logger.info(f"Stored hero decayed states: {len(hero_decay_states)} records")
    if player_hero_decay_states:
        await history_repo.upsert_player_hero_decayed_states(player_hero_decay_states)
        logger.info(f"Stored player-hero decayed states: {len(player_hero_decay_states)} records")
    if team_decay_states:
        await history_repo.upsert_team_decayed_states(team_decay_states)
        logger.info(f"Stored team decayed states: {len(team_decay_states)} records")
    if team_matchup_decay_states:
        await history_repo.upsert_team_matchup_decayed_states(team_matchup_decay_states)
        logger.info(f"Stored team matchup decayed states: {len(team_matchup_decay_states)} records")


async def get_all_matches(db_session: AsyncSession) -> List[MatchTable]:
    logger.info("Fetching all match details from the database...")
    match_repo = MatchRepository(db_session)
    all_matches = await match_repo.get_match_details(relationship_fields=["outcome"])

    logger.info(f"Fetched {len(all_matches)} matches from the database.")
    return all_matches


def filter_completed_matches(match_instances: List[MatchTable]) -> List[MatchTable]:
    """Return only matches that have a known outcome (radiant_win is not None).

    Some records may include an outcome object with a null/unknown radiant_win. Those
    should be excluded because generators rely on outcomes to update states; including
    them would leave states unchanged and features at priors (e.g., 0.5).
    """
    completed: List[MatchTable] = []
    for match in match_instances:
        out = getattr(match, "outcome", None)
        if out is None:
            continue
        if getattr(out, "radiant_win", None) is None:
            continue
        completed.append(match)
    return completed


if __name__ == "__main__":
    import asyncio

    asyncio.run(backfill_all_historical_matches())
