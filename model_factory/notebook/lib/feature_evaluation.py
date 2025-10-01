import lightgbm as lgb
import shap
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from typing import Tuple, Any

def run_shap_binary_classifier_test(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    n_estimators: int = 100,
    random_state: int = 42,
    show_plot: bool = True,
) -> Tuple[lgb.LGBMClassifier, shap.TreeExplainer, np.ndarray]:
    """
    Trains a LightGBM binary classifier and computes its SHAP values.

    This function serves as a diagnostic tool to:
    1. Create a fresh, isolated LGBMClassifier to ensure a binary objective.
    2. Fit the model on the provided training data.
    3. Verify the model's objective post-training.
    4. Use SHAP's TreeExplainer to calculate SHAP values on the test set.
    5. Analyze the structure of the returned SHAP values, which is expected
       to be a single NumPy array for binary classification with TreeExplainer.
    6. Optionally display the SHAP summary plot.

    Args:
        X_train: DataFrame containing the training features.
        y_train: Series containing the training target variable.
        X_test: DataFrame containing the test features for SHAP value calculation.
        n_estimators: The number of boosting rounds.
        random_state: Seed for reproducibility.
        show_plot: If True, displays the SHAP summary plot.

    Returns:
        A tuple containing:
        - model (lgb.LGBMClassifier): The trained LightGBM model.
        - explainer (shap.TreeExplainer): The fitted SHAP explainer.
        - shap_values (np.ndarray): The calculated SHAP values. For a binary
          classifier, this is a single array for the positive class.
    """
    # --- Step 1: Create a fresh, guaranteed-binary model ---
    print("\n[1/5] Creating a new, isolated LGBMClassifier with objective='binary'")
    model = lgb.LGBMClassifier(
        objective='binary',
        random_state=random_state,
        verbosity=-1,
        n_estimators=n_estimators
    )

    # --- Step 2: Ensure y_train is in the correct integer format ---
    y_train_int = y_train.astype(int)

    # --- Step 3: Fit the fresh model ---
    print("[2/5] Fitting the isolated model...")
    model.fit(X_train, y_train_int)

    # --- Step 4: Immediately verify its parameters AFTER fitting ---
    print("\n[3/5] Verifying the fitted model's parameters...")
    params = model.get_params()
    print(f"  - Model Objective: {params.get('objective')}")
    print(f"  - Model Class: {type(model)}")
    assert params.get('objective') == 'binary', "ISOLATION TEST FAILED: The model objective is NOT 'binary'."
    print("  - VERIFICATION SUCCEEDED: The model is definitively a binary classifier.")

    # --- Step 5: Immediately pass THIS EXACT model to SHAP ---
    print("\n[4/5] Creating SHAP explainer with the verified model...")
    explainer = None
    shap_values = None
    try:
        explainer = shap.TreeExplainer(model)

        print("[5/5] Calculating SHAP values...")
        shap_values = explainer.shap_values(X_test, check_additivity=False)

        # --- FINAL DIAGNOSTIC ---
        print("\n--- Final SHAP values structure ---")
        if isinstance(shap_values, list):
            print("  - WARNING: SHAP returned a list of arrays (unexpected for binary TreeExplainer).")
            # This logic is kept for robustness in case SHAP changes its behavior
            # or a different explainer is used.
            sv_positive_class = shap_values[1]
            print(f"  - Shape for positive class: {sv_positive_class.shape}")
            if show_plot:
                print("\nPlotting SHAP summary for positive class...")
                shap.summary_plot(sv_positive_class, X_test, show=False)
                plt.title("SHAP Summary (Positive Class from List)")
                plt.show()

        elif isinstance(shap_values, np.ndarray):
            print("  - SUCCESS (Expected behavior)! SHAP returned a single numpy array.")
            print("    (This array represents SHAP values for the positive class).")
            print(f"  - Shape of array: {shap_values.shape}")
            if show_plot:
                print("\nPlotting SHAP summary...")
                shap.summary_plot(shap_values, X_test, show=False)
                plt.title("SHAP Summary (from NumPy Array)")
                plt.show()

        print("\n--- ISOLATION TEST COMPLETE ---")

    except Exception as e:
        print(f"\nAN ERROR OCCURRED DURING THE SHAP ANALYSIS: {e}")
        # Ensure we return something even on failure
        return model, None, None
        
    return model, explainer, shap_values