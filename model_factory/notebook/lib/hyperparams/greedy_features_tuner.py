from dota_oracle_pipeline.feature_engineering.batch import (
    TeamDecayFeatureGenerator,
    PlayerHeroDynamicPriorFeatureGenerator,
    HeroWinrateDecayFeatureGenerator,
)
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
from typing import Any, Dict, List, Optional

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

TRIALS_MULTIPLIER = 15  # Multiplier to determine number of trials based on number of parameters

# Database setup for Optuna
DB_FILENAME = "../data/feature_tuning.db"
STORAGE_URL = f"sqlite:///{DB_FILENAME}"


class FeatureTuner:
    def __init__(
        self,
        model: Any,
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

        self.study_team_decay: Optional[optuna.study.Study] = None
        self.study_hero_decay: Optional[optuna.study.Study] = None
        self.study_player_hero: Optional[optuna.study.Study] = None

        # Validation strategy: "cross_validation" (default) or "train_test"
        if validation_split not in ("cross_validation", "train_test"):
            raise ValueError("validation_split must be either 'cross_validation' or 'train_test'")
        self.validation_split = validation_split

    def get_studies(self) -> Dict[str, optuna.study.Study]:
        """
        Returns the Optuna study objects after tuning is complete.

        Raises:
            RuntimeError: If this method is called before tune_features() has been run.

        Returns:
            Dict[str, optuna.study.Study]: A dictionary containing the study objects for
                                          'team_decay', 'hero_decay', and 'player_hero'.
        """
        if not all([self.study_team_decay, self.study_hero_decay, self.study_player_hero]):
            raise RuntimeError("Tuning has not been run yet. Please call the tune_features() method first.")

        return {
            "team_decay": self.study_team_decay,
            "hero_decay": self.study_hero_decay,
            "player_hero": self.study_player_hero,
        }  # type: ignore

    def tune_features(self) -> FeatureHyperparams:

        # --- Stage 0: Generate Default (untuned) Features ---
        print("Generating default features...")
        default_hero_winrate_decay_features = self.hero_winrate_decay_generator.generate(self.sorted_match_list)
        default_player_hero_dynamic_prior_features = self.player_hero_dynamic_prior_generator.generate(
            self.sorted_match_list
        )

        untuned_hero_df = pd.DataFrame(instance.model_dump() for instance in default_hero_winrate_decay_features)
        untuned_player_hero_df = pd.DataFrame(
            instance.model_dump() for instance in default_player_hero_dynamic_prior_features
        )

        # --- Stage 1: Tune Team Decay Features ---
        print("\n--- Starting Stage 1: Tuning Team Decay Features ---")
        self.study_team_decay = self._create_study("team_decay_tuning_study" + self.study_name_suffix)
        self.study_team_decay.optimize(
            lambda trial: self._objective_tune_team_features(trial, untuned_hero_df, untuned_player_hero_df),
            n_trials=TRIALS_MULTIPLIER * len(TEAM_DECAY_CONFIG),
        )
        best_team_params = self.study_team_decay.best_params
        print(f"Best Team Decay Params: {best_team_params}")

        # Generate tuned team features for the next stage
        tuned_team_features = self.team_decay_generator.generate(
            self.sorted_match_list,
            prior_mean=best_team_params["prior_mean"],
            prior_count=best_team_params["prior_count"],
            half_life_days=best_team_params["half_life_days"],
        )
        tuned_team_df = pd.DataFrame(instance.model_dump() for instance in tuned_team_features)

        # --- Stage 2: Tune Hero Winrate Decay Features ---
        print("\n--- Starting Stage 2: Tuning Hero Winrate Decay Features ---")
        self.study_hero_decay = self._create_study("hero_winrate_decay_tuning_study" + self.study_name_suffix)
        self.study_hero_decay.optimize(
            lambda trial: self._objective_tune_hero_features(trial, tuned_team_df, untuned_player_hero_df),
            n_trials=TRIALS_MULTIPLIER * len(HERO_WINRATE_DECAY_CONFIG),
        )
        best_hero_params = self.study_hero_decay.best_params
        print(f"Best Hero Decay Params: {best_hero_params}")

        # Generate tuned hero features for the next stage
        tuned_hero_features = self.hero_winrate_decay_generator.generate(
            self.sorted_match_list,
            prior_mean=best_hero_params["prior_mean"],
            prior_count=best_hero_params["prior_count"],
            half_life_days=best_hero_params["half_life_days"],
        )
        tuned_hero_df = pd.DataFrame(instance.model_dump() for instance in tuned_hero_features)

        # --- Stage 3: Tune Player-Hero Dynamic Prior Features ---
        print("\n--- Starting Stage 3: Tuning Player-Hero Dynamic Prior Features ---")
        self.study_player_hero = self._create_study("player_hero_dynamic_prior_tuning_study" + self.study_name_suffix)
        self.study_player_hero.optimize(
            lambda trial: self._objective_tune_player_hero_features(trial, tuned_team_df, tuned_hero_df),
            n_trials=TRIALS_MULTIPLIER * len(PLAYER_HERO_DYNAMIC_PRIOR_CONFIG),
        )
        best_player_hero_params = self.study_player_hero.best_params
        print(f"Best Player-Hero Params: {best_player_hero_params}")

        # --- Final Stage: Consolidate and Return ---
        print("\nFeature tuning complete!")

        best_team_hyperparams = TeamFeaturesHyperparams(**best_team_params)
        best_hero_hyperparams = HeroFeaturesHyperparams(**best_hero_params)
        best_player_hero_hyperparams = PlayerHeroFeaturesHyperparams(**best_player_hero_params)

        return FeatureHyperparams(
            team_features=best_team_hyperparams,
            hero_features=best_hero_hyperparams,
            player_hero_features=best_player_hero_hyperparams,
        )

    # Removed alpha/beta conversion: generators accept k/m directly.

    def _create_study(self, study_name: str, storage_url=STORAGE_URL) -> optuna.study.Study:
        return optuna.create_study(
            sampler=optuna.samplers.TPESampler(seed=42, multivariate=True, group=True),
            direction=self.direction,
            study_name=study_name,
            storage=storage_url,
        )

    def _evaluate_feature_set(self, X: pd.DataFrame, y: pd.Series) -> float:
        """
        Evaluate the current model on provided features/labels using the configured validation strategy.

        - cross_validation: TimeSeriesSplit with n_splits
        - train_test: single unshuffled 80/20 split (tail 20% as validation)
        """
        if self.validation_split == "cross_validation":
            time_series_cv = TimeSeriesSplit(n_splits=self.num_split)
            scores = cross_val_score(self.model, X, y, cv=time_series_cv, scoring=self.evaluation_metric, n_jobs=-1)
            return float(scores.mean())

        # train_test: simple chronological split (no shuffle), last 20% is validation
        n = len(X)
        if n < 5:
            # Fallback to small CV if dataset too small for a 20% split
            n_splits = max(2, min(3, n))
            time_series_cv = TimeSeriesSplit(n_splits=n_splits)
            scores = cross_val_score(self.model, X, y, cv=time_series_cv, scoring=self.evaluation_metric, n_jobs=-1)
            return float(scores.mean())

        # Use sklearn's train_test_split with shuffle=False to preserve chronology
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, shuffle=False)

        model = clone(self.model)
        model.fit(X_train, y_train)

        scorer = get_scorer(self.evaluation_metric)
        score = scorer(model, X_val, y_val)
        return float(score)

    def _objective_tune_team_features(
        self, trial: optuna.trial.Trial, untuned_hero_df: pd.DataFrame, untuned_player_hero_df: pd.DataFrame
    ) -> float:
        # 1. Suggest parameters for tuning
        params = {
            "prior_mean": trial.suggest_float(
                "prior_mean",
                TEAM_DECAY_CONFIG["prior_mean"]["low"],
                TEAM_DECAY_CONFIG["prior_mean"]["high"],
            ),
            "prior_count": trial.suggest_float(
                "prior_count",
                TEAM_DECAY_CONFIG["prior_count"]["low"],
                TEAM_DECAY_CONFIG["prior_count"]["high"],
                log=True,
            ),
            "half_life_days": trial.suggest_categorical(
                "half_life_days",
                TEAM_DECAY_CONFIG["half_life_days"],
            ),
        }

        # 2. Generate features with suggested parameters
        team_decay_features = self.team_decay_generator.generate(
            self.sorted_match_list,
            prior_mean=params["prior_mean"],
            prior_count=params["prior_count"],
            half_life_days=params["half_life_days"],
        )
        team_decay_df = pd.DataFrame(instance.model_dump() for instance in team_decay_features)

        # 3. Combine with other features and evaluate
        combined_df = merge_features_on_match_id(
            [self.train_outcome_df, team_decay_df, untuned_hero_df, untuned_player_hero_df]
        )
        y = combined_df["radiant_win"]
        X = combined_df.drop(columns=["match_id", "radiant_win"])

        return self._evaluate_feature_set(X, y)

    def _objective_tune_hero_features(
        self, trial: optuna.trial.Trial, tuned_team_df: pd.DataFrame, untuned_player_hero_df: pd.DataFrame
    ) -> float:
        # 1. Suggest parameters for tuning
        params = {
            "prior_mean": trial.suggest_float(
                "prior_mean",
                HERO_WINRATE_DECAY_CONFIG["prior_mean"]["low"],
                HERO_WINRATE_DECAY_CONFIG["prior_mean"]["high"],
            ),
            "prior_count": trial.suggest_float(
                "prior_count",
                HERO_WINRATE_DECAY_CONFIG["prior_count"]["low"],
                HERO_WINRATE_DECAY_CONFIG["prior_count"]["high"],
                log=True,
            ),
            "half_life_days": trial.suggest_categorical(
                "half_life_days",
                HERO_WINRATE_DECAY_CONFIG["half_life_days"],
            ),
        }

        # 2. Generate features with suggested parameters
        hero_winrate_decay_features = self.hero_winrate_decay_generator.generate(
            self.sorted_match_list,
            prior_mean=params["prior_mean"],
            prior_count=params["prior_count"],
            half_life_days=params["half_life_days"],
        )
        hero_winrate_decay_df = pd.DataFrame(instance.model_dump() for instance in hero_winrate_decay_features)

        # 3. Combine with other features and evaluate
        combined_df = merge_features_on_match_id(
            [self.train_outcome_df, tuned_team_df, hero_winrate_decay_df, untuned_player_hero_df]
        )
        y = combined_df["radiant_win"]
        X = combined_df.drop(columns=["match_id", "radiant_win"])

        return self._evaluate_feature_set(X, y)

    def _objective_tune_player_hero_features(
        self, trial: optuna.trial.Trial, tuned_team_df: pd.DataFrame, tuned_hero_df: pd.DataFrame
    ) -> float:
        # 1. Suggest parameters for tuning
        params = {
            "player_prior_count": trial.suggest_float(
                "player_prior_count",
                PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["player_prior_count"]["low"],
                PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["player_prior_count"]["high"],
                log=True,
            ),
            "player_half_life_days": trial.suggest_categorical(
                "player_half_life_days",
                PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["player_half_life_days"],
            ),
            "hero_prior_mean": trial.suggest_float(
                "hero_prior_mean",
                PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_prior_mean"]["low"],
                PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_prior_mean"]["high"],
            ),
            "hero_prior_count": trial.suggest_float(
                "hero_prior_count",
                PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_prior_count"]["low"],
                PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_prior_count"]["high"],
                log=True,
            ),
            "hero_half_life_days": trial.suggest_categorical(
                "hero_half_life_days",
                PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_half_life_days"],
            ),
        }

        # 2. Generate features with suggested parameters
        player_hero_features = self.player_hero_dynamic_prior_generator.generate(
            self.sorted_match_list,
            player_prior_count=params["player_prior_count"],
            player_half_life_days=params["player_half_life_days"],
            hero_prior_mean=params["hero_prior_mean"],
            hero_prior_count=params["hero_prior_count"],
            hero_half_life_days=params["hero_half_life_days"],
        )
        player_hero_df = pd.DataFrame(instance.model_dump() for instance in player_hero_features)

        # 3. Combine with other features and evaluate
        combined_df = merge_features_on_match_id([self.train_outcome_df, tuned_team_df, tuned_hero_df, player_hero_df])
        y = combined_df["radiant_win"]
        X = combined_df.drop(columns=["match_id", "radiant_win"])

        return self._evaluate_feature_set(X, y)
