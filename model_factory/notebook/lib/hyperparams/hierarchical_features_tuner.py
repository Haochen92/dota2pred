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

# Using a new DB file for this distinct tuning strategy
DB_FILENAME = "../data/feature_tuning_hierarchical.db"
STORAGE_URL = f"sqlite:///{DB_FILENAME}"


class HierarchicalFeatureTuner:
    """
    Tunes hyperparameters for feature generators in a staged, hierarchical manner
    to de-couple interdependent parameters like timescale and regularization.

    Stage 1: Tunes only `half_life_days` (timescale).
    Stage 2: Fixes timescale and tunes `prior_count` (regularization).
    Stage 3: Fixes timescale and regularization, then tunes `prior_mean`.
    """
    
    # Sensible defaults for parameters not being tuned in a given stage.
    DEFAULT_PRIOR_MEAN = 0.5
    DEFAULT_PRIOR_COUNT = 20.0 # A moderate level of regularization
    
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
        
        self.study_timescales: Optional[optuna.study.Study] = None
        self.study_priors: Optional[optuna.study.Study] = None
        self.study_prior_means: Optional[optuna.study.Study] = None
        
        if validation_split not in ("cross_validation", "train_test"):
            raise ValueError("validation_split must be either 'cross_validation' or 'train_test'")
        self.validation_split = validation_split

    def get_studies(self) -> Dict[str, optuna.study.Study]:
        """Returns the Optuna study objects for each stage after tuning is complete."""
        if not all([self.study_timescales, self.study_priors, self.study_prior_means]):
            raise RuntimeError("Tuning has not been run yet. Please call tune_features() first.")
        
        return {
            "timescales": self.study_timescales,
            "priors": self.study_priors,
            "prior_means": self.study_prior_means,
        } # type: ignore
        
    def tune_features(self) -> FeatureHyperparams:
        """Runs the hierarchical hyperparameter tuning process."""
        print("\n--- Starting Hierarchical Feature Tuning ---")
        
        # --- Stage 1: Tune Timescales (half_life_days) ---
        print("\n--- Stage 1: Tuning Timescales (half_life_days) ---")
        self.study_timescales = self._create_study("hierarchical_timescales_study" + self.study_name_suffix)
        # With a small search space, we don't need many trials.
        self.study_timescales.optimize(self._objective_tune_timescales, n_trials=40)
        best_timescale_params = self.study_timescales.best_params
        print(f"Best Timescale Params: {best_timescale_params}")

        # --- Stage 2: Tune Priors (prior_count) ---
        print("\n--- Stage 2: Tuning Priors (prior_count) using best timescales ---")
        self.study_priors = self._create_study("hierarchical_priors_study" + self.study_name_suffix)
        self.study_priors.optimize(
            lambda trial: self._objective_tune_priors(trial, best_timescale_params), 
            n_trials=40
        )
        best_prior_params = self.study_priors.best_params
        print(f"Best Prior Count Params: {best_prior_params}")
        
        # --- Stage 3: Tune Prior Means ---
        print("\n--- Stage 3: Tuning Prior Means using best timescales and priors ---")
        self.study_prior_means = self._create_study("hierarchical_prior_means_study" + self.study_name_suffix)
        self.study_prior_means.optimize(
            lambda trial: self._objective_tune_prior_means(trial, best_timescale_params, best_prior_params),
            n_trials=40
        )
        best_mean_params = self.study_prior_means.best_params
        print(f"Best Prior Mean Params: {best_mean_params}")
        
        # --- Final Stage: Consolidate and Return ---
        print("\nHierarchical feature tuning complete!")

        best_team_hyperparams = TeamFeaturesHyperparams(
            half_life_days=best_timescale_params['team_half_life_days'],
            prior_count=best_prior_params['team_prior_count'],
            prior_mean=best_mean_params['team_prior_mean'],
        )
        best_hero_hyperparams = HeroFeaturesHyperparams(
            half_life_days=best_timescale_params['hero_half_life_days'],
            prior_count=best_prior_params['hero_prior_count'],
            prior_mean=best_mean_params['hero_prior_mean'],
        )
        best_player_hero_hyperparams = PlayerHeroFeaturesHyperparams(
            player_half_life_days=best_timescale_params['player_half_life_days'],
            player_prior_count=best_prior_params['player_prior_count'],
            hero_half_life_days=best_timescale_params['player_hero_hero_half_life_days'],
            hero_prior_count=best_prior_params['player_hero_hero_prior_count'],
            hero_prior_mean=best_mean_params['player_hero_hero_prior_mean'],
        )

        return FeatureHyperparams(
            team_features=best_team_hyperparams,
            hero_features=best_hero_hyperparams,
            player_hero_features=best_player_hero_hyperparams,
        )

    def _objective_tune_timescales(self, trial: optuna.trial.Trial) -> float:
        """Objective for Stage 1: Tunes only half_life_days."""
        # 1. Suggest only timescale parameters
        team_half_life = trial.suggest_categorical("team_half_life_days", TEAM_DECAY_CONFIG["half_life_days"])
        hero_half_life = trial.suggest_categorical("hero_half_life_days", HERO_WINRATE_DECAY_CONFIG["half_life_days"])
        player_half_life = trial.suggest_categorical("player_half_life_days", PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["player_half_life_days"])
        player_hero_hero_half_life = trial.suggest_categorical("player_hero_hero_half_life_days", PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_half_life_days"])

        # 2. Generate features using suggested timescales and fixed defaults for others
        team_features = self.team_decay_generator.generate(self.sorted_match_list, half_life_days=team_half_life, prior_count=self.DEFAULT_PRIOR_COUNT, prior_mean=self.DEFAULT_PRIOR_MEAN)
        hero_features = self.hero_winrate_decay_generator.generate(self.sorted_match_list, half_life_days=hero_half_life, prior_count=self.DEFAULT_PRIOR_COUNT, prior_mean=self.DEFAULT_PRIOR_MEAN)
        player_hero_features = self.player_hero_dynamic_prior_generator.generate(
            self.sorted_match_list,
            player_half_life_days=player_half_life,
            hero_half_life_days=player_hero_hero_half_life,
            player_prior_count=self.DEFAULT_PRIOR_COUNT,
            hero_prior_count=self.DEFAULT_PRIOR_COUNT,
            hero_prior_mean=self.DEFAULT_PRIOR_MEAN
        )
        
        return self._combine_and_evaluate(team_features, hero_features, player_hero_features)

    def _objective_tune_priors(self, trial: optuna.trial.Trial, timescale_params: Dict[str, Any]) -> float:
        """Objective for Stage 2: Tunes only prior_count, using fixed best timescales."""
        # 1. Suggest only prior count parameters
        team_prior = trial.suggest_float("team_prior_count", **TEAM_DECAY_CONFIG["prior_count"], log=True)
        hero_prior = trial.suggest_float("hero_prior_count", **HERO_WINRATE_DECAY_CONFIG["prior_count"], log=True)
        player_prior = trial.suggest_float("player_prior_count", **PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["player_prior_count"], log=True)
        player_hero_hero_prior = trial.suggest_float("player_hero_hero_prior_count", **PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_prior_count"], log=True)
        
        # 2. Generate features using fixed timescales, suggested priors, and default mean
        team_features = self.team_decay_generator.generate(self.sorted_match_list, half_life_days=timescale_params['team_half_life_days'], prior_count=team_prior, prior_mean=self.DEFAULT_PRIOR_MEAN)
        hero_features = self.hero_winrate_decay_generator.generate(self.sorted_match_list, half_life_days=timescale_params['hero_half_life_days'], prior_count=hero_prior, prior_mean=self.DEFAULT_PRIOR_MEAN)
        player_hero_features = self.player_hero_dynamic_prior_generator.generate(
            self.sorted_match_list,
            player_half_life_days=timescale_params['player_half_life_days'],
            hero_half_life_days=timescale_params['player_hero_hero_half_life_days'],
            player_prior_count=player_prior,
            hero_prior_count=player_hero_hero_prior,
            hero_prior_mean=self.DEFAULT_PRIOR_MEAN
        )
        
        return self._combine_and_evaluate(team_features, hero_features, player_hero_features)

    def _objective_tune_prior_means(self, trial: optuna.trial.Trial, timescale_params: Dict[str, Any], prior_params: Dict[str, Any]) -> float:
        """Objective for Stage 3: Tunes only prior_mean, using fixed best timescales and priors."""
        # 1. Suggest only prior mean parameters
        team_mean = trial.suggest_float("team_prior_mean", **TEAM_DECAY_CONFIG["prior_mean"])
        hero_mean = trial.suggest_float("hero_prior_mean", **HERO_WINRATE_DECAY_CONFIG["prior_mean"])
        player_hero_hero_mean = trial.suggest_float("player_hero_hero_prior_mean", **PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_prior_mean"])
        
        # 2. Generate features using fixed timescales and priors, and suggested means
        team_features = self.team_decay_generator.generate(self.sorted_match_list, half_life_days=timescale_params['team_half_life_days'], prior_count=prior_params['team_prior_count'], prior_mean=team_mean)
        hero_features = self.hero_winrate_decay_generator.generate(self.sorted_match_list, half_life_days=timescale_params['hero_half_life_days'], prior_count=prior_params['hero_prior_count'], prior_mean=hero_mean)
        player_hero_features = self.player_hero_dynamic_prior_generator.generate(
            self.sorted_match_list,
            player_half_life_days=timescale_params['player_half_life_days'],
            hero_half_life_days=timescale_params['player_hero_hero_half_life_days'],
            player_prior_count=prior_params['player_prior_count'],
            hero_prior_count=prior_params['player_hero_hero_prior_count'],
            hero_prior_mean=player_hero_hero_mean
        )
        
        return self._combine_and_evaluate(team_features, hero_features, player_hero_features)

    def _combine_and_evaluate(self, team_features, hero_features, player_hero_features) -> float:
        """Helper to reduce code duplication in objective functions."""
        team_df = pd.DataFrame(instance.model_dump() for instance in team_features)
        hero_df = pd.DataFrame(instance.model_dump() for instance in hero_features)
        player_hero_df = pd.DataFrame(instance.model_dump() for instance in player_hero_features)

        combined_df = merge_features_on_match_id([self.train_outcome_df, team_df, hero_df, player_hero_df])
        y = combined_df['radiant_win']
        X = combined_df.drop(columns=['match_id', 'radiant_win'])
        
        return self._evaluate_feature_set(X, y)
    
    # The following helper methods are identical to the original class and can be reused directly.
    def _create_study(self, study_name: str, storage_url=STORAGE_URL) -> optuna.study.Study:
        return optuna.create_study(
            sampler=optuna.samplers.TPESampler(seed=42), # Multivariate not needed for smaller search spaces
            direction=self.direction,
            study_name=study_name,
            storage=storage_url,
            load_if_exists=True,
        )

    def _evaluate_feature_set(self, X: pd.DataFrame, y: pd.Series) -> float:
        """Evaluates the model on the provided feature set using the configured validation strategy."""
        if self.validation_split == "cross_validation":
            time_series_cv = TimeSeriesSplit(n_splits=self.num_split)
            scores = cross_val_score(
                self.model, X, y, cv=time_series_cv, scoring=self.evaluation_metric, n_jobs=-1
            )
            return float(scores.mean())

        # train_test split logic remains the same
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, shuffle=False)
        model = clone(self.model)
        model.fit(X_train, y_train)
        scorer = get_scorer(self.evaluation_metric)
        score = scorer(model, X_val, y_val)
        return float(score)