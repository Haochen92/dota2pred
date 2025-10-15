import pandas as pd
import numpy as np
from typing import Any, Dict, Optional

# Import the models and metrics
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score, get_scorer
from sklearn.model_selection import TimeSeriesSplit
import optuna

optuna.logging.set_verbosity(optuna.logging.WARNING)


DB_FILENAME = "model_tuning.db"
STORAGE_URL = f"sqlite:///{DB_FILENAME}"



class ModelTuner:
    """
    A reusable class for tuning and validating various models using Optuna.

    This class supports 'lightgbm', 'xgboost', 'random_forest', and 
    'logistic_regression'. It uses TimeSeriesSplit cross-validation, supports
    pruning for faster tuning, and provides a method for final validation
    on a held-out test set.
    """
    
    def __init__(
        self,
        model_name: str,
        X_train: pd.DataFrame,
        y_train: pd.DataFrame,             ## CHANGED: Now accepts a DataFrame
        target_column: str,                ## ADDED: To specify the target variable in y_train
        num_split: int = 5,
        evaluation_metric: str = "roc_auc", # CHANGED: Switched default to a more robust metric
        direction: str = "maximize",
        random_state: int = 42,            ## ADDED: For reproducibility
    ):
        """
        Args:
            model_name (str): The name of the model to tune. Supported: 
                              'lightgbm', 'xgboost', 'random_forest', 'logistic_regression'.
            X_train (pd.DataFrame): The training features.
            y_train (pd.DataFrame): The training labels DataFrame.
            target_column (str): The name of the column in y_train that contains the target variable.
            num_split (int): The number of splits for TimeSeriesSplit cross-validation.
            evaluation_metric (str): The scikit-learn scoring metric to optimize.
            direction (str): The direction of optimization ('maximize' or 'minimize').
            random_state (int): Seed for reproducibility.
        """
        self.model_name = model_name.lower()
        self.X_train = X_train
        self.y_train = y_train
        self.target_column = target_column ## ADDED
        self.num_split = num_split
        self.evaluation_metric = evaluation_metric
        self.direction = direction
        self.random_state = random_state   ## ADDED
        self.study: Optional[optuna.study.Study] = None
        
        self.model_map = {
            "lightgbm": LGBMClassifier,
            "xgboost": XGBClassifier,
            "random_forest": RandomForestClassifier,
            "logistic_regression": LogisticRegression,
        }
        
        if self.model_name not in self.model_map:
            raise ValueError(f"Unsupported model_name: '{self.model_name}'. "
                             f"Supported models are: {list(self.model_map.keys())}")
        
        # Ensure the target column exists in the provided y_train DataFrame
        if self.target_column not in self.y_train.columns:
            raise ValueError(f"Target column '{self.target_column}' not found in y_train DataFrame.")

    def get_study(self) -> optuna.study.Study:
        if not self.study:
            raise RuntimeError("Tuning has not been run. Please call tune() first.")
        return self.study

    def tune(self, n_trials: int, study_name: Optional[str] = None) -> Dict[str, Any]:
        if not study_name:
            study_name = f"{self.model_name}_{self.evaluation_metric}_tuning"

        print(f"\n--- Starting Hyperparameter Tuning for {self.model_name.upper()} ---")
        print(f"Optimizing for: {self.evaluation_metric.upper()}")
        print(f"Number of trials: {n_trials}")
        
        self.study = self._create_study(study_name)
        self.study.optimize(self._objective, n_trials=n_trials, n_jobs=-1)
        
        print("\n--- Tuning Complete ---")
        print(f"Best CV {self.evaluation_metric}: {self.study.best_value:.4f}")
        print(f"Best parameters found: {self.study.best_params}")
        return self.study.best_params

    def validate_on_test_set(self, X_test: pd.DataFrame, y_test: pd.DataFrame) -> Dict[str, float]:
        """
        Retrains the model with the best found parameters on the full training set
        and evaluates it on the held-out test set.

        Args:
            X_test (pd.DataFrame): The feature DataFrame for the test set.
            y_test (pd.DataFrame): The target DataFrame for the test set.

        Returns:
            A dictionary containing performance metrics on the test set.
        """
        if not self.study or not self.study.best_params:
            raise RuntimeError("Tuning must be run successfully before validation.")
        
        # Ensure the target column exists in the test DataFrame
        if self.target_column not in y_test.columns:
            raise ValueError(f"Target column '{self.target_column}' not found in y_test DataFrame.")

        print(f"\n--- Validating Best {self.model_name.upper()} Model on Test Set ---")
        
        best_params = self.study.best_params
        print(f"Using parameters: {best_params}")
        
        model_class = self.model_map[self.model_name]
        
        final_params = self._get_default_params()
        final_params.update(best_params)
        
        final_model = model_class(**final_params)
        
        # Extract the target series from the DataFrame for fitting
        y_train_series = self.y_train[self.target_column]
        final_model.fit(self.X_train, y_train_series)

        # Extract the target series from the test DataFrame for evaluation
        y_test_series = y_test[self.target_column]
        y_pred_proba = final_model.predict_proba(X_test)[:, 1]
        y_pred = final_model.predict(X_test)
        
        metrics = {
            "accuracy": accuracy_score(y_test_series, y_pred),
            "log_loss": log_loss(y_test_series, y_pred_proba),
            "roc_auc": roc_auc_score(y_test_series, y_pred_proba),
        }
        
        print("\nTest Set Performance:")
        for metric, value in metrics.items():
            print(f"  - {metric.replace('_', ' ').title()}: {value:.4f}")
            
        return metrics

    def _objective(self, trial: optuna.trial.Trial) -> float:
        params = self._suggest_params(trial)
        model_class = self.model_map[self.model_name]
        model = model_class(**params)
        
        cv = TimeSeriesSplit(n_splits=self.num_split)
        
        # Using get_scorer to handle any valid sklearn scoring string
        scorer = get_scorer(self.evaluation_metric)
        scores = []
        
        y_train_series = self.y_train[self.target_column]

        # Manual cross-validation loop to enable pruning
        for fold, (train_idx, val_idx) in enumerate(cv.split(self.X_train)):
            X_train_fold, X_val_fold = self.X_train.iloc[train_idx], self.X_train.iloc[val_idx]
            y_train_fold, y_val_fold = y_train_series.iloc[train_idx], y_train_series.iloc[val_idx]

            model.fit(X_train_fold, y_train_fold)
            score = scorer(model, X_val_fold, y_val_fold)
            scores.append(score)

            # Report intermediate results for pruning
            trial.report(score, fold)
            if trial.should_prune():
                raise optuna.TrialPruned()

        return float(np.mean(scores))
    
    def _suggest_params(self, trial: optuna.trial.Trial) -> Dict[str, Any]:
        """Helper to define the search space for each model."""
        base_params = self._get_default_params()
        if self.model_name == "lightgbm":
            params = {
                "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.2, log=True),
                "n_estimators": trial.suggest_int("n_estimators", 100, 2000, step=100),
                "num_leaves": trial.suggest_int("num_leaves", 20, 500),
                "max_depth": trial.suggest_int("max_depth", 3, 12),
                "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
                "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            }
        elif self.model_name == "xgboost":
             params = {
                "learning_rate": trial.suggest_float("learning_rate", 1e-3, 0.2, log=True), ## CHANGED: alias for eta
                "n_estimators": trial.suggest_int("n_estimators", 100, 2000, step=100),
                "max_depth": trial.suggest_int("max_depth", 3, 12),
                "lambda": trial.suggest_float("lambda", 1e-8, 10.0, log=True), # L2
                "alpha": trial.suggest_float("alpha", 1e-8, 10.0, log=True),   # L1
            }
        elif self.model_name == "random_forest":
            params = {
                "n_estimators": trial.suggest_int("n_estimators", 100, 1500, step=100),
                "max_depth": trial.suggest_int("max_depth", 5, 50),
                "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
                "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 20),
                "criterion": trial.suggest_categorical("criterion", ["gini", "entropy"]),
            }
        elif self.model_name == "logistic_regression":
            params = {
                "C": trial.suggest_float("C", 1e-5, 1e4, log=True),
                "penalty": trial.suggest_categorical("penalty", ["l1", "l2"]),
            }
        else:
            return {}
        
        base_params.update(params)
        return base_params
    
    def _get_default_params(self) -> Dict[str, Any]:
        """Returns a dictionary of default, non-tuned parameters for each model."""
        ## CHANGED: Uses self.random_state
        if self.model_name == "lightgbm":
            return {"objective": "binary", "metric": "binary_logloss", "verbosity": -1, "random_state": self.random_state}
        elif self.model_name == "xgboost":
            return {"objective": "binary:logistic", "eval_metric": "logloss", "seed": self.random_state}
        elif self.model_name == "random_forest":
            return {"random_state": self.random_state, "n_jobs": -1}
        elif self.model_name == "logistic_regression":
            return {"random_state": self.random_state, "solver": "liblinear", "max_iter": 1000}
        return {}

    def _create_study(self, study_name: str, storage_url=STORAGE_URL) -> optuna.study.Study:
        return optuna.create_study(
            sampler=optuna.samplers.TPESampler(seed=self.random_state),
            pruner=optuna.pruners.MedianPruner(), ## ADDED: Pruner for efficiency
            direction=self.direction,
            study_name=study_name,
            storage=storage_url,
            load_if_exists=True,
        )
