import pandas as pd
from typing import List

from dota_oracle_common.models.features.schema import TeamFeatures, HeroFeatures, PlayerHeroFeature, AllFeaturesDTO


def create_final_features(
    team_features_list: List[TeamFeatures],
    hero_features_list: List[HeroFeatures],
    player_hero_features_list: List[PlayerHeroFeature],
) -> List[AllFeaturesDTO]:
    """
    The main pipeline orchestrator.
    1. Converts Pydantic models to DataFrames.
    2. Merges them into a single source of truth.
    3. Runs the modular aggregation functions.
    4. Selects final columns and converts back to DTOs.
    """
    # 1. Ingest and Convert
    df_team = pd.DataFrame([f.model_dump() for f in team_features_list])
    df_hero = pd.DataFrame([f.model_dump() for f in hero_features_list])
    df_player = pd.DataFrame([f.model_dump() for f in player_hero_features_list])

    # 2. Merge into a single raw feature DataFrame
    df_raw = pd.merge(df_team, df_hero, on="match_id")
    df_raw = pd.merge(df_raw, df_player, on="match_id")

    # 3. Apply the modular aggregation pipeline
    df_processed = (
        df_raw.pipe(aggregate_team_features).pipe(aggregate_hero_features).pipe(aggregate_player_hero_features)
    )

    # 4. Finalise and Convert Back
    final_columns = list(AllFeaturesDTO.model_fields.keys())
    print(final_columns)

    # Ensure all required columns exist before selecting
    for col in final_columns:
        if col not in df_processed.columns:
            raise KeyError(f"Final column '{col}' not found in the processed DataFrame!")

    df_final = df_processed[final_columns]

    return [AllFeaturesDTO.model_validate(row) for row in df_final.to_dict(orient="records")]


def aggregate_team_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates and appends aggregated team features to the DataFrame."""
    df_out = df.copy()

    df_out["radiant_dire_team_wr_diff"] = df_out["radiant_win_rate"] - df_out["dire_win_rate"]

    return df_out


def aggregate_hero_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates and appends aggregated hero features to the DataFrame."""
    df_out = df.copy()

    radiant_hero_cols = [f"hero_{i}_win_rate" for i in range(5)]
    dire_hero_cols = [f"hero_{i}_win_rate" for i in range(128, 133)]

    df_out["radiant_avg_hero_wr"] = df_out[radiant_hero_cols].mean(axis=1)
    df_out["dire_avg_hero_wr"] = df_out[dire_hero_cols].mean(axis=1)
    df_out["radiant_dire_hero_wr_diff"] = df_out["radiant_avg_hero_wr"] - df_out["dire_avg_hero_wr"]

    return df_out


def aggregate_player_hero_features(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates and appends aggregated player-hero features to the DataFrame."""
    df_out = df.copy()

    radiant_player_cols = [f"player_hero_{i}_win_rate" for i in range(5)]
    dire_player_cols = [f"player_hero_{i}_win_rate" for i in range(128, 133)]

    df_out["radiant_avg_player_hero_wr"] = df_out[radiant_player_cols].mean(axis=1)
    df_out["dire_avg_player_hero_wr"] = df_out[dire_player_cols].mean(axis=1)
    df_out["radiant_dire_player_wr_diff"] = df_out["radiant_avg_player_hero_wr"] - df_out["dire_avg_player_hero_wr"]

    return df_out
