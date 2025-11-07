import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from prefect import flow, task

from dota_oracle_common.constants.endpoint_configs import service_url
from dota_oracle_common.http_client import http_client_provider
from dota_oracle_common.models.features import (
    AllFeaturesDTO,
    HeroFeaturesTable,
    PlayerHeroFeatureTable,
    TeamFeaturesTable,
)
from dota_oracle_common.models.histories import (
    HeroDecayedStateTable,
    PlayerHeroDecayedStateTable,
    TeamDecayedStateTable,
    TeamMatchupDecayedStateTable,
)
from dota_oracle_common.models.inference import MatchPredictionTable
from dota_oracle_common.models.inference.schema import (
    ModelMetaDataAPIResponse,
    ModelPredictionAPIResponse,
)
from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.postgresql import DatabaseManager
from dota_oracle_common.repositories.features_repository import FeaturesRepository
from dota_oracle_common.repositories.history_repository import HistoryRepository
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.repositories.prediction_repository import PredictionRepository
from dota_oracle_common.utils import get_current_utc_iso_timestamp, get_logger
from dota_oracle_pipeline.feature_engineering.batch.hero_wr_features.decay import (
    BatchHeroWinrateDecayFeatureGenerator,
)
from dota_oracle_pipeline.feature_engineering.batch.player_hero_features.dynamic_prior import (
    BatchPlayerHeroDynamicPriorFeatureGenerator,
)
from dota_oracle_pipeline.feature_engineering.batch.team_features.decay import (
    BatchTeamDecayFeatureGenerator,
)
from dota_oracle_pipeline.feature_transformation.aggregate_features import (
    create_final_features,
)
from dota_oracle_pipeline.inference.model_inference_service import ModelInferenceService

logger = get_logger(__name__)

# --- Configuration Constants ---
HALF_LIFE_DAYS = 60
STATE_WARMUP_MULTIPLIER = 5  # Generates state history for 5x half-life days before the gap
INFERENCE_BATCH_SIZE = 2000


# --- Data Structures for Clarity ---
@dataclass
class BackfillWindow:
    """Defines the time window for the backfill process."""

    window_start_time: datetime  # Earliest time to fetch matches for state warm-up
    gap_start_time: datetime  # Earliest time for which features/predictions need storing
    end_time: datetime  # End of the processing window (usually now)


@dataclass
class FeatureGenerationOutput:
    """Holds all features and states generated for the window."""

    team_features: List[TeamFeaturesTable]
    hero_features: List[HeroFeaturesTable]
    player_hero_features: List[PlayerHeroFeatureTable]
    hero_states: List[HeroDecayedStateTable]
    player_hero_states: List[PlayerHeroDecayedStateTable]
    team_states: List[TeamDecayedStateTable]
    team_matchup_states: List[TeamMatchupDecayedStateTable]


# --- Modular Tasks ---


@task(name="Fetch Model Metadata")
async def fetch_model_metadata() -> ModelMetaDataAPIResponse:
    """Fetches metadata for the pro match prediction model."""
    async with http_client_provider() as http_client:
        return await ModelInferenceService.fetch_model_metadata(
            http_client=http_client, metadata_url=service_url.PRO_MATCHES_METADATA_URL
        )


@task(name="Determine Backfill Window")
async def determine_backfill_window(predictor_name: str, max_lookback_days: Optional[int]) -> Optional[BackfillWindow]:
    """
    Determines the time window for backfilling based on the earliest missing data.
    Returns None if no gap is found or the gap is too old.
    """
    session_factory = DatabaseManager.get_session_factory()
    async with session_factory() as session:
        feat_repo = FeaturesRepository(session)
        pred_repo = PredictionRepository(session)

        earliest_feat_time = await feat_repo.get_earliest_missing_features_time()
        earliest_pred_time = await pred_repo.get_earliest_missing_prediction_time(predictor_name)

    candidates = [dt for dt in [earliest_feat_time, earliest_pred_time] if dt is not None]
    if not candidates:
        logger.info("No missing features or predictions found. Backfill not required.")
        return None

    gap_start_time = min(candidates)
    now = get_current_utc_iso_timestamp()

    if max_lookback_days is not None:
        lookback_threshold = now - timedelta(days=max_lookback_days)
        if gap_start_time < lookback_threshold:
            logger.warning(
                f"Earliest gap at {gap_start_time.isoformat()} is older than the max lookback "
                f"of {max_lookback_days} days. Skipping backfill."
            )
            return None

    warmup_days = STATE_WARMUP_MULTIPLIER * HALF_LIFE_DAYS
    window_start_time = gap_start_time - timedelta(days=warmup_days)

    return BackfillWindow(window_start_time=window_start_time, gap_start_time=gap_start_time, end_time=now)


@task(name="Fetch Matches in Window")
async def fetch_matches_in_window(window: BackfillWindow) -> List[MatchTable]:
    """Fetches all completed match details within the specified time window."""
    session_factory = DatabaseManager.get_session_factory()
    async with session_factory() as session:
        match_repo = MatchRepository(session)
        matches = await match_repo.get_match_details(
            relationship_fields=["outcome"], start_time=window.window_start_time, end_time=window.end_time
        )

    # Filter for matches that have a conclusive outcome
    completed_matches = [m for m in matches if getattr(getattr(m, "outcome", None), "radiant_win", None) is not None]
    return completed_matches


@task(name="Generate Features and States")
def generate_features_and_states(matches: List[MatchTable]) -> FeatureGenerationOutput:
    """Generates all features and historical states for the given matches."""
    hero_gen = BatchHeroWinrateDecayFeatureGenerator()
    ph_gen = BatchPlayerHeroDynamicPriorFeatureGenerator()
    team_gen = BatchTeamDecayFeatureGenerator()

    hero_features, hero_states = hero_gen.generate(matches, prior_mean=0.5, prior_count=50, half_life_days=45)
    player_hero_features, player_hero_states = ph_gen.generate(
        matches,
        player_prior_count=8,
        player_half_life_days=60,
        hero_prior_count=50,
        hero_prior_mean=0.5,
        hero_half_life_days=45,
    )
    team_features, team_states, team_matchup_states = team_gen.generate(
        matches, prior_mean=0.52, prior_count=13, half_life_days=45
    )

    return FeatureGenerationOutput(
        hero_features=hero_features,
        hero_states=hero_states,
        player_hero_features=player_hero_features,
        player_hero_states=player_hero_states,
        team_features=team_features,
        team_states=team_states,
        team_matchup_states=team_matchup_states,
    )


@task(name="Store Backfill Data")
async def store_backfill_data(
    generated_data: FeatureGenerationOutput, target_match_ids: List[int]
) -> FeatureGenerationOutput:
    """
    Filters generated data to the relevant gap window and persists it to the database.
    Returns the filtered data for use in prediction.
    """

    target_ids = set(int(mid) for mid in target_match_ids)

    def _filter_by_match_id(items, ids):
        return [item for item in items if int(getattr(item, "match_id", 0)) in ids]

    # Summary before filtering
    total_counts = {
        "team_features": len(generated_data.team_features),
        "hero_features": len(generated_data.hero_features),
        "player_hero_features": len(generated_data.player_hero_features),
        "hero_states": len(generated_data.hero_states),
        "player_hero_states": len(generated_data.player_hero_states),
        "team_states": len(generated_data.team_states),
        "team_matchup_states": len(generated_data.team_matchup_states),
    }

    # Filter all generated data to only include records from the target matches
    filtered_data = FeatureGenerationOutput(
        team_features=_filter_by_match_id(generated_data.team_features, target_ids),
        hero_features=_filter_by_match_id(generated_data.hero_features, target_ids),
        player_hero_features=_filter_by_match_id(generated_data.player_hero_features, target_ids),
        hero_states=_filter_by_match_id(generated_data.hero_states, target_ids),
        player_hero_states=_filter_by_match_id(generated_data.player_hero_states, target_ids),
        team_states=_filter_by_match_id(generated_data.team_states, target_ids),
        team_matchup_states=_filter_by_match_id(generated_data.team_matchup_states, target_ids),
    )

    filtered_counts = {
        "team_features": len(filtered_data.team_features),
        "hero_features": len(filtered_data.hero_features),
        "player_hero_features": len(filtered_data.player_hero_features),
        "hero_states": len(filtered_data.hero_states),
        "player_hero_states": len(filtered_data.player_hero_states),
        "team_states": len(filtered_data.team_states),
        "team_matchup_states": len(filtered_data.team_matchup_states),
    }

    logger.info(
        "Backfill generation summary (window vs persisted): "
        f"team_features={total_counts['team_features']}→{filtered_counts['team_features']}, "
        f"hero_features={total_counts['hero_features']}→{filtered_counts['hero_features']}, "
        f"player_hero_features={total_counts['player_hero_features']}→{filtered_counts['player_hero_features']}, "
        f"hero_states={total_counts['hero_states']}→{filtered_counts['hero_states']}, "
        f"player_hero_states={total_counts['player_hero_states']}→{filtered_counts['player_hero_states']}, "
        f"team_states={total_counts['team_states']}→{filtered_counts['team_states']}, "
        f"team_matchup_states={total_counts['team_matchup_states']}→{filtered_counts['team_matchup_states']}"
    )

    session_factory = DatabaseManager.get_session_factory()
    async with session_factory() as session:
        features_repo = FeaturesRepository(session)
        history_repo = HistoryRepository(session)

        if filtered_data.hero_features:
            await features_repo.store_features(filtered_data.hero_features, HeroFeaturesTable)
        if filtered_data.player_hero_features:
            await features_repo.store_features(filtered_data.player_hero_features, PlayerHeroFeatureTable)
        if filtered_data.team_features:
            await features_repo.store_features(filtered_data.team_features, TeamFeaturesTable)

        if filtered_data.hero_states:
            await history_repo.upsert_hero_decayed_states(filtered_data.hero_states)
        if filtered_data.player_hero_states:
            await history_repo.upsert_player_hero_decayed_states(filtered_data.player_hero_states)
        if filtered_data.team_states:
            await history_repo.upsert_team_decayed_states(filtered_data.team_states)
        if filtered_data.team_matchup_states:
            await history_repo.upsert_team_matchup_decayed_states(filtered_data.team_matchup_states)

        await session.commit()

    return filtered_data


@task(name="Aggregate and Align Features")
def aggregate_and_align_features(
    features_to_predict: FeatureGenerationOutput, model_metadata: ModelMetaDataAPIResponse
) -> Tuple[np.ndarray, np.ndarray]:
    """Aggregates feature tables and aligns them with the model's expected schema."""
    all_features_dto: List[AllFeaturesDTO] = create_final_features(
        team_features_list=features_to_predict.team_features,
        hero_features_list=features_to_predict.hero_features,
        player_hero_features_list=features_to_predict.player_hero_features,
    )

    df = pd.DataFrame([f.model_dump() for f in all_features_dto])
    if df.empty:
        return np.array([]), np.array([])

    meta_cols = list(model_metadata.version_metadata.feature_columns or [])
    feature_cols = [c for c in meta_cols if c != "match_id"]
    if not feature_cols:  # Fallback if metadata is missing feature columns
        feature_cols = [c for c in AllFeaturesDTO.model_fields.keys() if c != "match_id"]

    missing_cols = [c for c in feature_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Final aggregated features are missing required columns: {missing_cols}")

    X = df[feature_cols].to_numpy()
    match_ids = df["match_id"].to_numpy()
    return X, match_ids


@task(name="Run Inference")
async def run_inference(X: np.ndarray, match_ids: np.ndarray, model_metadata: ModelMetaDataAPIResponse) -> List[dict]:
    """Runs model inference in batches and returns prediction results."""
    if X.size == 0:
        return []

    results = []
    async with http_client_provider() as http_client:
        service = ModelInferenceService(
            http_client=http_client,
            model_metadata=model_metadata,
            prediction_url=service_url.PRO_MATCHES_INFERENCE_URL,
        )
        for i in range(0, X.shape[0], INFERENCE_BATCH_SIZE):
            batch_X = X[i : i + INFERENCE_BATCH_SIZE]
            batch_ids = match_ids[i : i + INFERENCE_BATCH_SIZE]

            response: ModelPredictionAPIResponse = await service.get_prediction(batch_X)
            preds = response.prediction or []
            probs = response.probability or []

            for j, mid in enumerate(batch_ids):
                results.append(
                    {
                        "match_id": int(mid),
                        "prediction": preds[j] if j < len(preds) else None,
                        "probability": probs[j] if j < len(probs) else None,
                    }
                )
    return results


@task(name="Store Predictions")
async def store_predictions(predictions: List[dict], model_metadata: ModelMetaDataAPIResponse):
    """Stores batch prediction results in the database."""
    if not predictions:
        return 0

    to_upsert = [
        MatchPredictionTable(
            match_id=p["match_id"],
            predictor_name=model_metadata.name,
            predictor_version=model_metadata.version,
            prediction=bool(p["prediction"]) if p["prediction"] is not None else None,
            prediction_probability=p["probability"],
            prediction_date=get_current_utc_iso_timestamp(),
        )
        for p in predictions
    ]

    session_factory = DatabaseManager.get_session_factory()
    async with session_factory() as session:
        pred_repo = PredictionRepository(session)
        await pred_repo.store_match_predictions_bulk(to_upsert)
        await session.commit()

    return len(to_upsert)


# --- Main Prefect Flow ---


@flow(name="Scheduled Pro-Match Backfill", retries=2, retry_delay_seconds=30)
async def scheduled_backfill_flow(max_lookback_days: Optional[int] = None):
    """
    A scheduled flow to find gaps in pro-match features or predictions and backfill them.

    1. Determines the earliest data gap.
    2. Fetches matches in a wide window to warm up historical state.
    3. Generates features and states for all matches in the window.
    4. Persists the new features and states for matches within the gap.
    5. Runs inference on the newly generated features.
    6. Stores the new predictions.
    """
    model_metadata = await fetch_model_metadata()
    window = await determine_backfill_window(model_metadata.name, max_lookback_days)

    if not window:
        return {"processed_matches": 0, "stored_predictions": 0}

    logger.info(
        f"Backfill window determined: "
        f"State warm-up from {window.window_start_time.isoformat()}, "
        f"persisting data from {window.gap_start_time.isoformat()}."
    )

    matches = await fetch_matches_in_window(window)
    if not matches:
        logger.info("No completed matches found in the specified window. Exiting.")
        return {"processed_matches": 0, "stored_predictions": 0}

    all_generated_data = generate_features_and_states(matches)

    # Determine target IDs (matches from the gap onward)
    target_match_ids = [m.match_id for m in matches if m.start_time >= window.gap_start_time]

    # Store data only for the gap, but use all generated data for context
    data_for_prediction = await store_backfill_data(all_generated_data, target_match_ids)

    X, match_ids = aggregate_and_align_features(data_for_prediction, model_metadata)

    predictions = await run_inference(X, match_ids, model_metadata)

    num_stored = await store_predictions(predictions, model_metadata)

    logger.info(f"Backfill complete. Stored {num_stored} predictions for {len(match_ids)} matches.")

    return {"processed_matches": len(match_ids), "stored_predictions": num_stored}


if __name__ == "__main__":
    asyncio.run(scheduled_backfill_flow(max_lookback_days=365))
