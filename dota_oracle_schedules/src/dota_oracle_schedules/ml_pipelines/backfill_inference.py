from prefect import flow, task
import pandas as pd
import numpy as np
from typing import Optional, List, Tuple
from dota_oracle_common.utils import get_logger

from dota_oracle_pipeline.inference.model_inference_service import ModelInferenceService
from dota_oracle_pipeline.feature_transformation.aggregate_features import create_final_features


from dota_oracle_common.repositories.features_repository import FeaturesRepository
from dota_oracle_common.repositories.prediction_repository import PredictionRepository

from dota_oracle_common.constants.endpoint_configs import service_url
from dota_oracle_common.http_client import http_client_provider
from dota_oracle_common.postgresql import database_session_factory_resource

from dota_oracle_common.models.features import (
    TeamFeaturesTable,
    HeroFeaturesTable,
    PlayerHeroFeatureTable,
    AllFeaturesDTO,
)
from dota_oracle_common.models.inference import MatchPredictionTable
from dota_oracle_common.utils import get_current_utc_iso_timestamp
from dota_oracle_common.models.inference.schema import ModelMetaDataAPIResponse


logger = get_logger(__name__)


@flow(name="backfill model prediction from start", retries=2, retry_delay_seconds=10)
async def backfill_model_prediction_from_start():
    # 1) Fetch features from DB
    all_features_tables = await fetch_features_from_db()
    team_features, hero_features, player_hero_features = all_features_tables

    # 2) Build DTOs of aggregated features
    all_features_dto = await prepare_all_features_dto(
        team_features=team_features,
        hero_features=hero_features,
        player_hero_features=player_hero_features,
    )

    # 3) Fetch model metadata (for column alignment)
    model_metadata = await fetch_model_metadata()

    # 4) Prepare features in the exact order expected by the model
    features_array, match_ids = await prepare_features_for_inference(
        all_features_dto=all_features_dto,
        model_metadata=model_metadata,
    )

    # 5) Get predictions (batched)
    aligned_results = await get_predictions(features_array=features_array, match_ids=match_ids)

    # 6) Store predictions
    await store_predictions(aligned_results=aligned_results, model_metadata=model_metadata)

    return aligned_results


@task(name="fetch features from db")
async def fetch_features_from_db(
    match_ids: Optional[List[int]] = None,
) -> Tuple[List[TeamFeaturesTable], List[HeroFeaturesTable], List[PlayerHeroFeatureTable]]:
    async with database_session_factory_resource() as session_factory, session_factory() as db_session:
        features_repository = FeaturesRepository(session=db_session)
        team_features = await features_repository.get_team_features(match_ids=match_ids)
        hero_features = await features_repository.get_hero_features(match_ids=match_ids)
        player_hero_features = await features_repository.get_player_hero_features(match_ids=match_ids)

        return team_features, hero_features, player_hero_features


async def prepare_all_features_dto(
    team_features: List[TeamFeaturesTable],
    hero_features: List[HeroFeaturesTable],
    player_hero_features: List[PlayerHeroFeatureTable],
) -> List[AllFeaturesDTO]:
    all_features_dto = create_final_features(
        team_features_list=team_features,
        hero_features_list=hero_features,
        player_hero_features_list=player_hero_features,
    )
    return all_features_dto


@task(name="fetch model metadata")
async def fetch_model_metadata() -> ModelMetaDataAPIResponse:
    async with http_client_provider() as http_client:
        metadata = await ModelInferenceService.fetch_model_metadata(
            http_client=http_client,
            metadata_url=service_url.PRO_MATCHES_METADATA_URL,
        )
        return metadata


@task(name="prepare features for inference")
async def prepare_features_for_inference(
    all_features_dto: List[AllFeaturesDTO],
    model_metadata: ModelMetaDataAPIResponse,
) -> Tuple[np.ndarray, np.ndarray]:
    """Align and validate features for inference.

    - Builds a DataFrame from DTOs
    - Orders columns to match the model metadata
    - Drops non-feature identifiers (e.g., match_id) if present
    """
    all_features_df = pd.DataFrame([features.model_dump() for features in all_features_dto])

    if all_features_df.empty:
        logger.warning("No features available for inference.")
        return np.array([]), np.array([])

    # Use model-declared columns, but ensure identifiers like 'match_id' are not part of the features
    meta_columns = list(model_metadata.version_metadata.feature_columns or [])
    feature_columns = [c for c in meta_columns if c != "match_id"]

    # If metadata is missing or empty, fallback to DTO order minus 'match_id'
    if not feature_columns:
        feature_columns = [c for c in AllFeaturesDTO.model_fields.keys() if c != "match_id"]

    # Validate presence
    missing = [c for c in feature_columns if c not in all_features_df.columns]
    if missing:
        raise ValueError(f"Final features missing required columns: {missing}")

    # Select in correct order
    ordered_df = all_features_df[feature_columns]
    feature_array = ordered_df.to_numpy()
    match_ids = (
        all_features_df["match_id"].to_numpy() if "match_id" in all_features_df.columns else np.arange(len(ordered_df))
    )
    logger.info(f"Prepared features with shape {feature_array.shape} and {len(match_ids)} match_ids")
    return feature_array, match_ids


@task(name="get model predictions", retries=3, retry_delay_seconds=30)
async def get_predictions(features_array: np.ndarray, match_ids: np.ndarray):
    """Batch requests to the inference service and aggregate results.

    Sending very large payloads can cause server 500s or timeouts; this batches
    requests to keep payloads manageable.
    """
    if features_array.size == 0:
        return []

    BATCH_SIZE = 2000

    async with http_client_provider() as http_client:
        # Fetch metadata once to initialize the inference service
        model_metadata = await ModelInferenceService.fetch_model_metadata(
            http_client=http_client,
            metadata_url=service_url.PRO_MATCHES_METADATA_URL,
        )

        inference_service = ModelInferenceService(
            model_metadata=model_metadata,
            http_client=http_client,
            prediction_url=service_url.PRO_MATCHES_INFERENCE_URL,
        )

        try:
            aligned_results = []

            for start in range(0, features_array.shape[0], BATCH_SIZE):
                end = min(start + BATCH_SIZE, features_array.shape[0])
                batch = features_array[start:end]
                batch_ids = match_ids[start:end]

                resp = await inference_service.get_prediction(input_features=batch)

                preds = resp.prediction or []
                probs = resp.probability or []

                # Align each prediction to its match_id by position
                for i, mid in enumerate(batch_ids):
                    pred = preds[i] if i < len(preds) else None
                    prob = probs[i] if i < len(probs) else None
                    aligned_results.append({"match_id": int(mid), "prediction": pred, "probability": prob})

            return aligned_results
        except Exception as e:
            logger.error(f"Error during model inference: {e}")
            raise


@task(name="store predictions")
async def store_predictions(aligned_results: List[dict], model_metadata: ModelMetaDataAPIResponse) -> int:
    """Persist aligned predictions to the database using upsert semantics.

    Returns number of records stored/updated.
    """
    if not aligned_results:
        return 0

    stored = 0
    async with database_session_factory_resource() as session_factory, session_factory() as session:
        repo = PredictionRepository(session=session)
        to_upsert: List[MatchPredictionTable] = []
        for r in aligned_results:
            try:
                mp = MatchPredictionTable(
                    match_id=int(r["match_id"]),
                    predictor_name=model_metadata.name,
                    predictor_version=model_metadata.version,
                    prediction=(bool(r["prediction"]) if r.get("prediction") is not None else None),
                    prediction_probability=r.get("probability"),
                    prediction_date=get_current_utc_iso_timestamp(),
                )
                to_upsert.append(mp)
            except Exception as e:
                logger.error(
                    f"Invalid prediction payload for match_id={r.get('match_id')}: {e}",
                    exc_info=True,
                )
                continue

        if to_upsert:
            await repo.store_match_predictions_bulk(match_predictions=to_upsert)
            await session.commit()
            stored = len(to_upsert)

    logger.info(f"Stored/updated {stored} predictions (predictor={model_metadata.name} v{model_metadata.version}).")
    return stored
