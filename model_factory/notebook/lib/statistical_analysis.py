import pandas as pd
import numpy as np
from typing import Dict, Any
from sklearn.base import clone, BaseEstimator
from statsmodels.stats.contingency_tables import mcnemar

def compare_features_with_mcnemar(
    model: BaseEstimator,
    features_a_train: pd.DataFrame,
    features_a_test: pd.DataFrame,
    features_b_train: pd.DataFrame,
    features_b_test: pd.DataFrame,
    y_train_df: pd.DataFrame,
    y_test_df: pd.DataFrame,
    merge_key: str = "match_id",
    target_col: str = "radiant_win"
) -> Dict[str, float]:
    """
    Trains a model on two different feature sets (A and B) and compares their
    accuracy on a test set using McNemar's test for statistical significance.

    Args:
        model: A scikit-learn compatible classifier instance.
        features_a_train: Training features for the baseline configuration (A).
        features_a_test: Test features for the baseline configuration (A).
        features_b_train: Training features for the new/tuned configuration (B).
        features_b_test: Test features for the new/tuned configuration (B).
        y_train_df: DataFrame with training labels and merge_key.
        y_test_df: DataFrame with test labels and merge_key.
        merge_key: The column name to join on (e.g., 'match_id').
        target_col: The column name of the target variable.

    Returns:
        A dictionary containing the accuracies of both models and the p-value.
    """
    
    def _train_and_predict(X_train_feat, y_train_df, X_test_feat, y_test_df):
        """Nested helper to train a model and return aligned predictions."""
        # Prepare training data
        train_df = pd.merge(y_train_df, X_train_feat, on=merge_key)
        X_train = train_df.drop(columns=[merge_key, target_col])
        y_train = train_df[target_col]

        # Prepare test data to ensure perfect alignment
        test_df = pd.merge(y_test_df, X_test_feat, on=merge_key)
        X_test = test_df.drop(columns=[merge_key, target_col])
        y_true = test_df[target_col]
        
        # Train and predict
        fitted_model = clone(model).fit(X_train, y_train)
        y_pred = fitted_model.predict(X_test)
        
        return y_pred, y_true

    # Train models and get aligned predictions for both feature sets
    y_pred_a, y_true = _train_and_predict(features_a_train, y_train_df, features_a_test, y_test_df)
    y_pred_b, _      = _train_and_predict(features_b_train, y_train_df, features_b_test, y_test_df)

    # --- McNemar's Test Logic ---
    a_right = (y_pred_a == y_true)
    b_right = (y_pred_b == y_true)

    # b: cases where Model A was right and B was wrong
    # c: cases where Model A was wrong and B was right
    b = np.sum(a_right & ~b_right)
    c = np.sum(~a_right & b_right)

    table = [[0, b], [c, 0]]
    
    # Use exact binomial test for small sample sizes, otherwise chi-squared
    use_exact = (b + c) < 25
    result = mcnemar(table, exact=use_exact, correction=not use_exact)
    p_value = result.pvalue
    
    # --- Reporting ---
    acc_a = a_right.mean()
    acc_b = b_right.mean()

    print("--- McNemar's Test for Statistical Significance ---")
    print(f"Model A (Baseline) Accuracy: {acc_a:.4f}")
    print(f"Model B (Tuned)    Accuracy: {acc_b:.4f}")
    print(f"Accuracy Difference (B - A): {acc_b - acc_a:+.4f}")
    print(f"\nDiscordant Pairs: A_correct/B_wrong = {b}, A_wrong/B_correct = {c}")
    print(f"McNemar's Test p-value: {p_value:.4f}")

    if p_value < 0.05:
        print("\nResult: The difference in accuracy IS statistically significant (p < 0.05).")
    else:
        print("\nResult: The difference in accuracy is NOT statistically significant (p >= 0.05).")

    return {"accuracy_a": acc_a, "accuracy_b": acc_b, "p_value": p_value}