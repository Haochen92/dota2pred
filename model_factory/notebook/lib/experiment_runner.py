import pandas as pd
from typing import Dict, Any, List
from .model_evaluation import evaluate_models
from .utils import merge_features_on_match_id


def run_experiment(
    feature_sets_train: List[pd.DataFrame],
    y_train_df: pd.DataFrame,
    feature_sets_test: List[pd.DataFrame],
    y_test_df: pd.DataFrame,
    models_dict: Dict[str, Any],
    target_col: str = "radiant_win",
    merge_key: str = "match_id",
) -> None:
    """
    Minimal experiment runner.
    - Merges feature sets with targets
    - Aligns test columns to train
    - Trains each model once and reports accuracy
    """
    print("Starting new experiment run...\n")
    
    # merge features and targets to ensure final row alignment
    all_train_dfs = feature_sets_train + [y_train_df]
    final_df_train = merge_features_on_match_id(all_train_dfs, on_key=merge_key)
    
    all_test_dfs = feature_sets_test + [y_test_df]
    final_df_test = merge_features_on_match_id(all_test_dfs, on_key=merge_key)

    X_train = final_df_train.drop(columns=[merge_key, target_col])
    X_test = final_df_test.drop(columns=[merge_key, target_col])

    y_train = final_df_train[target_col]
    y_test = final_df_test[target_col]


    results, leaderboard = evaluate_models(
        models=models_dict,
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test
    )
    print("\nExperiment completed. Leaderboard:")
    print(leaderboard)
