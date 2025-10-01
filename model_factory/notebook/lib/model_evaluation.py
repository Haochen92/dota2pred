from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb
import lightgbm as lgb

# ---- Reusable Training Utilities ----
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score


# Initialize models
Models = {
    'Logistic Regression': LogisticRegression(
        random_state=42,
        max_iter=1000  
    ),
    
    'Random Forest': RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        n_jobs=-1  # Use all cores
    ),
    
    'XGBoost': xgb.XGBClassifier(
        random_state=42,
        eval_metric='logloss',  # Suppress warning
        n_estimators=100
    ),
    
    'LightGBM': lgb.LGBMClassifier(
        random_state=42,
        objective='binary',
        verbosity=-1,  # Suppress output
        n_estimators=100
    )
}


def evaluate_models(models: Dict[str, Any],
                    X_train, y_train, X_test, y_test) -> Tuple[Dict[str, Any], pd.DataFrame]:
    """
    Fit and evaluate a dict of models. Returns:
    - results: dict[name] = { model, accuracy, predictions, probabilities }
    - leaderboard: DataFrame with columns [name, accuracy]
    """
    results: Dict[str, Any] = {}
    rows = []
    for name, model in models.items():
        print(f"\nTraining {name}...")
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        try:
            y_proba = model.predict_proba(X_test)[:, 1]
        except Exception:
            y_proba = None
        acc = accuracy_score(y_test, y_pred)
        results[name] = {
            'model': model,
            'accuracy': acc,
            'predictions': y_pred,
            'probabilities': y_proba,
        }
        rows.append({'name': name, 'accuracy': acc})
        print(f"{name} Accuracy: {acc:.3f} ({acc*100:.1f}%)")
    leaderboard = pd.DataFrame(rows).sort_values('accuracy', ascending=False).reset_index(drop=True)
    return results, leaderboard