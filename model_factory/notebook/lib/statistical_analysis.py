import pandas as pd
from typing import Dict
from sklearn.base import clone, BaseEstimator
from mlxtend.evaluate import mcnemar_table, mcnemar

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
    performance on a test set using McNemar's test via the mlxtend library.

    Args:
        model: A scikit-learn compatible classifier instance.
        # ... (rest of the docstring is the same as before) ...

    Returns:
        A dictionary containing the accuracies of both models and the p-value.
    """

    def _train_and_predict(X_train_feat, y_train_df, X_test_feat, y_test_df):
        """Nested helper to train a model and return aligned predictions."""
        train_df = pd.merge(y_train_df, X_train_feat, on=merge_key)
        X_train = train_df.drop(columns=[merge_key, target_col])
        y_train = train_df[target_col]

        test_df = pd.merge(y_test_df, X_test_feat, on=merge_key)
        X_test = test_df.drop(columns=[merge_key, target_col])
        y_true = test_df[target_col]
        
        fitted_model = clone(model).fit(X_train, y_train)
        y_pred = fitted_model.predict(X_test)
        
        return y_pred, y_true

    # Train models and get aligned predictions
    y_pred_a, y_true = _train_and_predict(features_a_train, y_train_df, features_a_test, y_test_df)
    y_pred_b, _      = _train_and_predict(features_b_train, y_train_df, features_b_test, y_test_df)

    # --- McNemar's Test Logic using mlxtend ---
    tb = mcnemar_table(y_target=y_true, y_model1=y_pred_a, y_model2=y_pred_b)
    
    # The mcnemar function handles the Chi-Squared calculation and p-value
    # It also internally handles the continuity correction by default
    chi2, p_value = mcnemar(ary=tb, corrected=True)
    
    # Extract discordant pairs for clear reporting
    a_correct_b_wrong = tb[0][1]
    a_wrong_b_correct = tb[1][0]
    
    # --- Reporting ---
    acc_a = (y_pred_a == y_true).mean()
    acc_b = (y_pred_b == y_true).mean()

    print("--- McNemar's Test for Statistical Significance ---")
    print(f"Model A (Baseline) Accuracy: {acc_a:.4f}")
    print(f"Model B (Tuned)    Accuracy: {acc_b:.4f}")
    print(f"Accuracy Difference (B - A): {acc_b - acc_a:+.4f}")
    print(f"\nDiscordant Pairs: A_correct/B_wrong = {a_correct_b_wrong}, A_wrong/B_correct = {a_wrong_b_correct}")
    print(f"McNemar's Test p-value: {p_value:.4f}")

    if p_value < 0.05:
        print("\nResult: The difference in performance IS statistically significant (p < 0.05).")
    else:
        print("\nResult: The difference in performance is NOT statistically significant (p >= 0.05).")

    return {"accuracy_a": acc_a, "accuracy_b": acc_b, "p_value": p_value}