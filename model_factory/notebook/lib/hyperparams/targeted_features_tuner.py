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
import numpy as np
from typing import Any, Dict, List, Optional
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


from sklearn.model_selection import TimeSeriesSplit, cross_val_score, train_test_split
from sklearn.metrics import get_scorer
from sklearn.base import clone

import optuna

optuna.logging.set_verbosity(optuna.logging.WARNING)

# Constants
HALF_DAYS_OPTIONS = [7, 14, 30, 45, 60, 90]
HERO_WINRATE_DECAY_CONFIG = {
    "prior_count": {"low": 10, "high": 1000},
    "half_life_days": HALF_DAYS_OPTIONS,
}
PLAYER_HERO_DYNAMIC_PRIOR_CONFIG = {
    "player_half_life_days": HALF_DAYS_OPTIONS,
    "hero_prior_count": HERO_WINRATE_DECAY_CONFIG["prior_count"],
    "hero_half_life_days": HERO_WINRATE_DECAY_CONFIG["half_life_days"],
}
TEAM_DECAY_CONFIG = {
    "half_life_days": HALF_DAYS_OPTIONS,
}


# Configuration for the new, smaller search space
TARGETED_CONFIG = {
    "hero_prior_count": HERO_WINRATE_DECAY_CONFIG["prior_count"],
    "team_half_life_days": TEAM_DECAY_CONFIG["half_life_days"],
    "hero_half_life_days": HERO_WINRATE_DECAY_CONFIG["half_life_days"],
    "player_half_life_days": PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["player_half_life_days"],
}

TRIALS_MULTIPLIER = 15
DB_FILENAME = "../data/feature_tuning_targeted.db"  # Using a new DB for this final run
STORAGE_URL = f"sqlite:///{DB_FILENAME}"


class TargetedFeatureTuner:
    """
    Performs a targeted ("Principled Hybrid") tuning run.

    - Fixes most priors based on domain knowledge and data analysis.
    - Tunes only the most uncertain parameters: all `half_life_days` and the
      `hero_prior_count` (shared between hero and player-hero features).
    """

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
        self.study: Optional[optuna.study.Study] = None

        if validation_split not in ("cross_validation", "train_test"):
            raise ValueError("validation_split must be either 'cross_validation' or 'train_test'")
        self.validation_split = validation_split

    def get_study(self) -> optuna.study.Study:
        if not self.study:
            raise RuntimeError("Tuning has not been run. Please call tune_features() first.")
        return self.study

    def analyze_study(self, top_n: int = 20) -> Dict[str, float]:
        study = self.get_study()
        df = study.trials_dataframe(attrs=("value", "user_attrs")).dropna()
        noise_floor = df["user_attrs_cv_std_dev"].mean()
        is_maximization = study.direction == optuna.study.StudyDirection.MAXIMIZE
        top_trials = df.sort_values("value", ascending=not is_maximization).head(top_n)
        stability = top_trials["value"].std()
        return {
            "avg_cv_std_dev (noise_floor)": noise_floor,
            "stability_of_top_trials": stability,
        }

    def visualize_analysis(self, top_n: int = 20):
        analysis_results = self.analyze_study(top_n=top_n)
        labels = ["Avg. CV Std Dev\n(Noise Floor)", f"Std Dev of Top {top_n} Trials\n(Tuning Stability)"]
        values = list(analysis_results.values())
        colors = ["#d9534f", "#5cb85c"]
        fig, ax = plt.subplots(figsize=(8, 6))
        bars = ax.bar(labels, values, color=colors, width=0.5)
        ax.set_title("Tuning Stability vs. Model Noise Floor", fontsize=16, pad=20)
        ax.set_ylabel("Standard Deviation (Performance Variance)")
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1.0, decimals=1))
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(axis="x", length=0, pad=10)
        for bar in bars:
            height = bar.get_height()
            ax.annotate(
                f"{height:.2%}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=12,
            )
        plt.tight_layout()
        plt.show()

    def tune_features(self) -> FeatureHyperparams:
        study_name = "targeted_feature_tuning_study" + self.study_name_suffix
        self.study = self._create_study(study_name)

        n_trials = TRIALS_MULTIPLIER * len(TARGETED_CONFIG)
        print(f"Running targeted tuning for {len(TARGETED_CONFIG)} parameters over {n_trials} trials.")

        self.study.optimize(self._objective_targeted, n_trials=n_trials)

        best_params = self.study.best_params
        print(f"Best Tuned Params: {best_params}")

        # --- Reconstruct the full hyperparameter set ---
        # Combine the tuned values with the fixed, sensible defaults
        final_team_params = {
            "prior_mean": 0.52,
            "prior_count": 13.0,
            "half_life_days": best_params["team_half_life_days"],
        }
        final_hero_params = {
            "prior_mean": 0.5,
            "prior_count": best_params["hero_prior_count"],
            "half_life_days": best_params["hero_half_life_days"],
        }
        final_player_hero_params = {
            "player_prior_count": 8.0,
            "player_half_life_days": best_params["player_half_life_days"],
            "hero_prior_mean": 0.5,
            "hero_prior_count": best_params["hero_prior_count"],  # Use the shared tuned value
            "hero_half_life_days": best_params["hero_half_life_days"],
        }

        return FeatureHyperparams(
            team_features=TeamFeaturesHyperparams(**final_team_params),
            hero_features=HeroFeaturesHyperparams(**final_hero_params),
            player_hero_features=PlayerHeroFeaturesHyperparams(**final_player_hero_params),
        )

    def _objective_targeted(self, trial: optuna.trial.Trial) -> float:
        # --- 1. Define the focused search space ---

        # Suggest only the parameters we want to tune
        tuned_params = {
            "hero_prior_count": trial.suggest_float(
                "hero_prior_count", **TARGETED_CONFIG["hero_prior_count"], log=True
            ),
            "team_half_life_days": trial.suggest_categorical(
                "team_half_life_days", TARGETED_CONFIG["team_half_life_days"]
            ),
            "hero_half_life_days": trial.suggest_categorical(
                "hero_half_life_days", TARGETED_CONFIG["hero_half_life_days"]
            ),
            "player_half_life_days": trial.suggest_categorical(
                "player_half_life_days", TARGETED_CONFIG["player_half_life_days"]
            ),
        }

        # --- 2. Combine tuned params with fixed, sensible defaults ---
        team_params = {
            "prior_mean": 0.52,
            "prior_count": 13.0,
            "half_life_days": tuned_params["team_half_life_days"],
        }
        hero_params = {
            "prior_mean": 0.5,
            "prior_count": tuned_params["hero_prior_count"],
            "half_life_days": tuned_params["hero_half_life_days"],
        }
        player_hero_params = {
            "player_prior_count": 8.0,
            "hero_prior_mean": 0.5,
            "player_half_life_days": tuned_params["player_half_life_days"],
            "hero_prior_count": tuned_params["hero_prior_count"],
            "hero_half_life_days": tuned_params["hero_half_life_days"],
        }

        # --- 3. Generate features and evaluate ---
        team_features = self.team_decay_generator.generate(self.sorted_match_list, **team_params)
        hero_features = self.hero_winrate_decay_generator.generate(self.sorted_match_list, **hero_params)
        player_hero_features = self.player_hero_dynamic_prior_generator.generate(
            self.sorted_match_list, **player_hero_params, verbose=False
        )

        team_df = pd.DataFrame(instance.model_dump() for instance in team_features)
        hero_df = pd.DataFrame(instance.model_dump() for instance in hero_features)
        player_hero_df = pd.DataFrame(instance.model_dump() for instance in player_hero_features)

        combined_df = merge_features_on_match_id([self.train_outcome_df, team_df, hero_df, player_hero_df])
        y = combined_df["radiant_win"]
        X = combined_df.drop(columns=["match_id", "radiant_win"])

        return self._evaluate_feature_set(X, y, trial)

    def _create_study(self, study_name: str, storage_url=STORAGE_URL) -> optuna.study.Study:
        # A simple sampler is fine for this smaller, more stable search space
        return optuna.create_study(
            sampler=optuna.samplers.TPESampler(seed=42),
            direction=self.direction,
            study_name=study_name,
            storage=storage_url,
            load_if_exists=True,
        )

    def _evaluate_feature_set(self, X: pd.DataFrame, y: pd.Series, trial: optuna.trial.Trial) -> float:
        if self.validation_split == "cross_validation":
            cv = TimeSeriesSplit(n_splits=self.num_split)
            scores = cross_val_score(self.model, X, y, cv=cv, scoring=self.evaluation_metric, n_jobs=-1)
            mean_score, std_dev = float(np.mean(scores)), float(np.std(scores))
            trial.set_user_attr("cv_std_dev", std_dev)
            trial.set_user_attr("fold_scores", scores.tolist())
            return mean_score

        trial.set_user_attr("cv_std_dev", 0.0)
        trial.set_user_attr("fold_scores", [])
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, shuffle=False)
        model = clone(self.model)
        model.fit(X_train, y_train)
        scorer = get_scorer(self.evaluation_metric)
        return float(scorer(model, X_val, y_val))
