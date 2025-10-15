from dota_oracle_pipeline.feature_engineering.batch import TeamDecayFeatureGenerator, PlayerHeroDynamicPriorFeatureGenerator, HeroWinrateDecayFeatureGenerator
from lib.utils import merge_features_on_match_id
from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.models.features.schema import (
    FeatureHyperparams,
    HeroFeaturesHyperparams,
    PlayerHeroFeaturesHyperparams,
    TeamFeaturesHyperparams,
)

# Imports
import pandas as pd
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

from sklearn.model_selection import TimeSeriesSplit, cross_val_score, train_test_split
from sklearn.metrics import get_scorer
from sklearn.base import clone

import optuna

optuna.logging.set_verbosity(optuna.logging.WARNING)

# Constants
HALF_DAYS_OPTIONS = [7, 14, 30, 45, 60, 90]

TEAM_DECAY_CONFIG = {
    "prior_mean": {"low": 0.45, "high": 0.55},
    "prior_count": {"low": 10.0, "high": 1000.0},
    "half_life_days": HALF_DAYS_OPTIONS,
}

HERO_WINRATE_DECAY_CONFIG = {
    "prior_mean": {"low": 0.45, "high": 0.55},
    "prior_count": {"low": 10, "high": 1000},
    "half_life_days": HALF_DAYS_OPTIONS,
}

PLAYER_HERO_DYNAMIC_PRIOR_CONFIG = {
    "player_prior_count": {"low": 5.0, "high": 1000.0},
    "player_half_life_days": HALF_DAYS_OPTIONS,
    "hero_prior_mean": HERO_WINRATE_DECAY_CONFIG["prior_mean"],
    "hero_prior_count": HERO_WINRATE_DECAY_CONFIG["prior_count"],
    "hero_half_life_days": HERO_WINRATE_DECAY_CONFIG["half_life_days"],
}

COMBINED_CONFIG = {
    **{f"team_{k}": v for k, v in TEAM_DECAY_CONFIG.items()},
    **{f"hero_{k}": v for k, v in HERO_WINRATE_DECAY_CONFIG.items()},
    **{f"player_hero_{k}": v for k, v in PLAYER_HERO_DYNAMIC_PRIOR_CONFIG.items()},
}

TRIALS_MULTIPLIER = 15
DB_FILENAME = "../data/feature_tuning_simultaneous.db"
STORAGE_URL = f"sqlite:///{DB_FILENAME}"


class SimultaneousFeatureTuner:
    """
    Tunes hyperparameters for all feature generators simultaneously, and provides
    methods to analyze the stability and significance of the results.
    """
    def __init__(
        self, model: Any, 
        train_outcome_df: pd.DataFrame, 
        sorted_match_list: List[MatchTable], 
        num_split: int = 5,
        evaluation_metric: str = "accuracy",
        direction: str = "maximize",
        study_name_suffix: str = "",
        validation_split: str = "cross_validation",
    ):
        self.team_decay_generator = TeamDecayFeatureGenerator()
        self.hero_winrate_decay_generator = HeroWinrateDecayFeatureGenerator()
        self.player_hero_dynamic_prior_generator = PlayerHeroDynamicPriorFeatureGenerator()
        self.model = model
        self.train_outcome_df = train_outcome_df
        self.sorted_match_list = sorted_match_list
        self.num_split = num_split
        self.evaluation_metric = evaluation_metric
        self.direction = direction
        self.study_name_suffix = study_name_suffix
        self.study: Optional[optuna.study.Study] = None
        
        if validation_split not in ("cross_validation", "train_test"):
            raise ValueError("validation_split must be either 'cross_validation' or 'train_test'")
        self.validation_split = validation_split
        
    def get_study(self) -> optuna.study.Study:
        if not self.study:
            raise RuntimeError("Tuning has not been run. Please call tune_features() first.")
        return self.study
    
    def analyze_study(self, top_n: int = 20) -> Dict[str, float]:
        """
        Analyzes the completed study for stability and noise.

        Args:
            top_n: The number of top trials to consider for the stability metric.

        Returns:
            A dictionary containing key analysis metrics.
        """
        study = self.get_study()
        df = study.trials_dataframe(attrs=("value", "user_attrs")).dropna()

        # Calculate the "noise floor" from the stored CV standard deviations
        noise_floor = df["user_attrs_cv_std_dev"].mean()

        # Calculate the stability of the best trials
        is_maximization = study.direction == optuna.study.StudyDirection.MAXIMIZE
        top_trials = df.sort_values("value", ascending=not is_maximization).head(top_n)
        stability = top_trials["value"].std()

        return {
            "avg_cv_std_dev (noise_floor)": noise_floor,
            "stability_of_top_trials": stability,
        }

    def tune_features(self) -> FeatureHyperparams:
        study_name = "simultaneous_feature_tuning_study" + self.study_name_suffix
        self.study = self._create_study(study_name)
        
        n_trials = TRIALS_MULTIPLIER * len(COMBINED_CONFIG)
        self.study.optimize(self._objective_simultaneous, n_trials=n_trials)
        
        best_params = self.study.best_params
        best_team_params = {k.replace("team_", ""): v for k, v in best_params.items() if k.startswith("team_")}
        best_hero_params = {k.replace("hero_", ""): v for k, v in best_params.items() if k.startswith("hero_")}
        best_player_hero_params = {
            "player_prior_count": best_params.get("player_prior_count"),
            "player_half_life_days": best_params.get("player_half_life_days"),
            "hero_prior_mean": best_params.get("player_hero_hero_prior_mean"),
            "hero_prior_count": best_params.get("player_hero_hero_prior_count"),
            "hero_half_life_days": best_params.get("player_hero_hero_half_life_days"),
        }

        return FeatureHyperparams(
            team_features=TeamFeaturesHyperparams(**best_team_params),
            hero_features=HeroFeaturesHyperparams(**best_hero_params),
            player_hero_features=PlayerHeroFeaturesHyperparams(**best_player_hero_params),
        )

    def _objective_simultaneous(self, trial: optuna.trial.Trial) -> float:
        team_params = {
            "prior_mean": trial.suggest_float("team_prior_mean", **TEAM_DECAY_CONFIG["prior_mean"]),
            "prior_count": trial.suggest_float("team_prior_count", **TEAM_DECAY_CONFIG["prior_count"], log=True),
            "half_life_days": trial.suggest_categorical("team_half_life_days", TEAM_DECAY_CONFIG["half_life_days"]),
        }
        hero_params = {
            "prior_mean": trial.suggest_float("hero_prior_mean", **HERO_WINRATE_DECAY_CONFIG["prior_mean"]),
            "prior_count": trial.suggest_float("hero_prior_count", **HERO_WINRATE_DECAY_CONFIG["prior_count"], log=True),
            "half_life_days": trial.suggest_categorical("hero_half_life_days", HERO_WINRATE_DECAY_CONFIG["half_life_days"]),
        }
        player_hero_params = {
            "player_prior_count": trial.suggest_float("player_prior_count", **PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["player_prior_count"], log=True),
            "player_half_life_days": trial.suggest_categorical("player_half_life_days", PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["player_half_life_days"]),
            "hero_prior_mean": trial.suggest_float("player_hero_hero_prior_mean", **PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_prior_mean"]),
            "hero_prior_count": trial.suggest_float("player_hero_hero_prior_count", **PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_prior_count"], log=True),
            "hero_half_life_days": trial.suggest_categorical("player_hero_hero_half_life_days", PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_half_life_days"]),
        }
        
        team_features = self.team_decay_generator.generate(self.sorted_match_list, **team_params)
        hero_features = self.hero_winrate_decay_generator.generate(self.sorted_match_list, **hero_params)
        player_hero_features = self.player_hero_dynamic_prior_generator.generate(self.sorted_match_list, **player_hero_params)
        
        team_df = pd.DataFrame(instance.model_dump() for instance in team_features)
        hero_df = pd.DataFrame(instance.model_dump() for instance in hero_features)
        player_hero_df = pd.DataFrame(instance.model_dump() for instance in player_hero_features)
        
        combined_df = merge_features_on_match_id([self.train_outcome_df, team_df, hero_df, player_hero_df])
        y = combined_df['radiant_win']
        X = combined_df.drop(columns=['match_id', 'radiant_win'])
        
        return self._evaluate_feature_set(X, y, trial)
    
    def _create_study(self, study_name: str, storage_url=STORAGE_URL) -> optuna.study.Study:
        return optuna.create_study(
            sampler=optuna.samplers.TPESampler(seed=42, multivariate=True, group=True),
            direction=self.direction,
            study_name=study_name,
            storage=storage_url,
            load_if_exists=True,
        )

    def _evaluate_feature_set(self, X: pd.DataFrame, y: pd.Series, trial: optuna.trial.Trial) -> float:
        if self.validation_split == "cross_validation":
            cv = TimeSeriesSplit(n_splits=self.num_split)
            scores = cross_val_score(self.model, X, y, cv=cv, scoring=self.evaluation_metric, n_jobs=-1)
            
            mean_score = float(np.mean(scores))
            std_dev = float(np.std(scores))
            
            trial.set_user_attr("cv_std_dev", std_dev)
            trial.set_user_attr("fold_scores", scores.tolist())
            
            return mean_score

        # For train_test split, std_dev isn't applicable
        trial.set_user_attr("cv_std_dev", 0.0)
        trial.set_user_attr("fold_scores", [])
        
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, shuffle=False)
        model = clone(self.model)
        model.fit(X_train, y_train)
        scorer = get_scorer(self.evaluation_metric)
        return float(scorer(model, X_val, y_val))