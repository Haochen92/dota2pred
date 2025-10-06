from typing import Any
from pydantic import BaseModel, Field
from dota_oracle_pipeline.feature_engineering.batch import TeamDecayFeatureGenerator, PlayerHeroDynamicPriorFeatureGenerator, HeroWinrateDecayFeatureGenerator
from lib.utils import merge_features_on_match_id
from dota_oracle_common.models.match import MatchTable

# Imports
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional

from sklearn.model_selection import TimeSeriesSplit, cross_val_score

import lightgbm as lgb
import optuna, optuna_dashboard
from optuna.visualization import (
    plot_optimization_history, plot_param_importances,
    plot_slice, plot_parallel_coordinate, plot_contour, plot_edf
)

optuna.logging.set_verbosity(optuna.logging.WARNING)

# Constants

TEAM_DECAY_CONFIG = {
    "alpha": {"low": 1, "high": 1000},
    "beta": {"low": 2, "high": 2000},
    "half_life_days": [7, 14, 30, 60, 90],
}

HERO_WINRATE_DECAY_CONFIG = {
    "alpha": {"low": 1, "high": 1000},
    "beta": {"low": 2, "high": 2000},
    "half_life_days": [7, 14, 30, 60, 90],
}

PLAYER_HERO_DYNAMIC_PRIOR_CONFIG = {
    "player_credibility_C": {"low": 1, "high": 1000},
    "player_half_life_days": [7, 14, 30, 60, 90, 180],
    "hero_alpha": HERO_WINRATE_DECAY_CONFIG["alpha"],
    "hero_beta": HERO_WINRATE_DECAY_CONFIG["beta"],
    "hero_half_life_days": HERO_WINRATE_DECAY_CONFIG["half_life_days"],
}

TRIALS_MULTIPLIER = 15  # Multiplier to determine number of trials based on number of parameters

# Database setup for Optuna
DB_FILENAME = "../data/feature_tuning.db" 
STORAGE_URL = f"sqlite:///{DB_FILENAME}"

class FeatureHyperparams(BaseModel):
    team_decay_alpha: int = Field(..., description="Alpha parameter for team decay feature")
    team_decay_beta: int = Field(..., description="Beta parameter for team decay feature")
    team_decay_half_life_days: int = Field(..., description="Half-life days for team decay feature")
    
    hero_decay_alpha: int = Field(..., description="Alpha parameter for hero winrate decay feature")
    hero_decay_beta: int = Field(..., description="Beta parameter for hero winrate decay feature")
    hero_decay_half_life_days: int = Field(..., description="Half-life days for hero winrate decay feature")
    
    player_credibility_C: int = Field(..., description="Credibility C for player-hero dynamic prior feature")
    player_half_life_days: int = Field(..., description="Half-life days for player-hero dynamic prior feature")
    player_hero_alpha: int = Field(..., description="Alpha parameter for hero winrate decay in player-hero dynamic prior feature")
    player_hero_beta: int = Field(..., description="Beta parameter for hero winrate decay in player-hero dynamic prior feature")
    player_hero_half_life_days: int = Field(..., description="Half-life days for hero winrate decay in player-hero dynamic prior feature")
    

class FeatureTuner:
    def __init__(
        self, model: Any, 
        train_outcome_df: pd.DataFrame, 
        sorted_match_list: List[MatchTable], 
        num_split: int = 5,
        evaluation_metric: str = "accuracy",
        direction: str = "maximize"
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
        
        self.study_team_decay: Optional[optuna.study.Study] = None
        self.study_hero_decay: Optional[optuna.study.Study] = None
        self.study_player_hero: Optional[optuna.study.Study] = None
        
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
        } # type: ignore

    def tune_features(self) -> FeatureHyperparams:
        
        # --- Stage 0: Generate Default (untuned) Features ---
        print("Generating default features...")
        default_hero_winrate_decay_features = self.hero_winrate_decay_generator.generate(
            self.sorted_match_list
        )
        default_player_hero_dynamic_prior_features = self.player_hero_dynamic_prior_generator.generate(
            self.sorted_match_list
        )
        
        untuned_hero_df = pd.DataFrame(instance.model_dump() for instance in default_hero_winrate_decay_features)
        untuned_player_hero_df = pd.DataFrame(instance.model_dump() for instance in default_player_hero_dynamic_prior_features)
        
        # --- Stage 1: Tune Team Decay Features ---
        print("\n--- Starting Stage 1: Tuning Team Decay Features ---")
        self.study_team_decay = self._create_study("Team Decay Tuning Study")
        self.study_team_decay.optimize(
            lambda trial: self._objective_tune_team_features(trial, untuned_hero_df, untuned_player_hero_df), 
            n_trials=TRIALS_MULTIPLIER * len(TEAM_DECAY_CONFIG)
        )
        best_team_params = self.study_team_decay.best_params
        print(f"Best Team Decay Params: {best_team_params}")

        # Generate tuned team features for the next stage
        tuned_team_features = self.team_decay_generator.generate(self.sorted_match_list, **best_team_params)
        tuned_team_df = pd.DataFrame(instance.model_dump() for instance in tuned_team_features)

        # --- Stage 2: Tune Hero Winrate Decay Features ---
        print("\n--- Starting Stage 2: Tuning Hero Winrate Decay Features ---")
        self.study_hero_decay = self._create_study("Hero Winrate Decay Tuning Study")
        self.study_hero_decay.optimize(
            lambda trial: self._objective_tune_hero_features(trial, tuned_team_df, untuned_player_hero_df),
            n_trials=TRIALS_MULTIPLIER * len(HERO_WINRATE_DECAY_CONFIG)
        )
        best_hero_params = self.study_hero_decay.best_params
        print(f"Best Hero Decay Params: {best_hero_params}")
        
        # Generate tuned hero features for the next stage
        tuned_hero_features = self.hero_winrate_decay_generator.generate(self.sorted_match_list, **best_hero_params)
        tuned_hero_df = pd.DataFrame(instance.model_dump() for instance in tuned_hero_features)
        
        # --- Stage 3: Tune Player-Hero Dynamic Prior Features ---
        print("\n--- Starting Stage 3: Tuning Player-Hero Dynamic Prior Features ---")
        self.study_player_hero = self._create_study("Player Hero Dynamic Prior Tuning Study")
        self.study_player_hero.optimize(
            lambda trial: self._objective_tune_player_hero_features(trial, tuned_team_df, tuned_hero_df),
            n_trials=TRIALS_MULTIPLIER * len(PLAYER_HERO_DYNAMIC_PRIOR_CONFIG)
        )
        best_player_hero_params = self.study_player_hero.best_params
        print(f"Best Player-Hero Params: {best_player_hero_params}")
        
        # --- Final Stage: Consolidate and Return ---
        print("\nFeature tuning complete!")
        
        # Consolidate all best parameters
        all_best_params = {
            **best_team_params,
            **best_hero_params,
            **best_player_hero_params
        }
        
        # Rename keys to match the Pydantic model fields
        final_params = {
            'team_decay_alpha': all_best_params['team_decay_alpha'],
            'team_decay_beta': all_best_params['team_decay_beta'],
            'team_decay_half_life_days': all_best_params['team_decay_half_life_days'],
            'hero_decay_alpha': all_best_params['hero_decay_alpha'],
            'hero_decay_beta': all_best_params['hero_decay_beta'],
            'hero_decay_half_life_days': all_best_params['hero_decay_half_life_days'],
            'player_credibility_C': all_best_params['player_credibility_C'],
            'player_half_life_days': all_best_params['player_half_life_days'],
            'player_hero_alpha': all_best_params['player_hero_alpha'],
            'player_hero_beta': all_best_params['player_hero_beta'],
            'player_hero_half_life_days': all_best_params['player_hero_half_life_days'],
        }

        return FeatureHyperparams(**final_params)
         
    def _create_study(self, study_name: str, storage_url=STORAGE_URL) -> optuna.study.Study:
        return optuna.create_study(
            sampler=optuna.samplers.TPESampler(),
            direction=self.direction,
            study_name=study_name,
            storage=storage_url,
            load_if_exists=True
        )

    def _objective_tune_team_features(self, trial: optuna.trial.Trial, untuned_hero_df: pd.DataFrame, untuned_player_hero_df: pd.DataFrame) -> float:
        # 1. Suggest parameters for tuning
        params = {
            "alpha": trial.suggest_int("alpha", TEAM_DECAY_CONFIG["alpha"]["low"], TEAM_DECAY_CONFIG["alpha"]["high"]),
            "beta": trial.suggest_int("beta", TEAM_DECAY_CONFIG["beta"]["low"], TEAM_DECAY_CONFIG["beta"]["high"]),
            "half_life_days": trial.suggest_categorical("half_life_days", TEAM_DECAY_CONFIG["half_life_days"])
        }

        # 2. Generate features with suggested parameters
        team_decay_features = self.team_decay_generator.generate(self.sorted_match_list, **params)
        team_decay_df = pd.DataFrame(instance.model_dump() for instance in team_decay_features)

        # 3. Combine with other features and evaluate
        combined_df = merge_features_on_match_id([self.train_outcome_df, team_decay_df, untuned_hero_df, untuned_player_hero_df])
        y = combined_df['radiant_win']
        X = combined_df.drop(columns=['match_id', 'radiant_win'])
        
        time_series_cv = TimeSeriesSplit(n_splits=self.num_split)
        scores = cross_val_score(self.model, X, y, cv=time_series_cv, scoring=self.evaluation_metric, n_jobs=-1)
        
        return scores.mean()
    
    def _objective_tune_hero_features(self, trial: optuna.trial.Trial, tuned_team_df: pd.DataFrame, untuned_player_hero_df: pd.DataFrame) -> float:
        # 1. Suggest parameters for tuning
        params = {
            "alpha": trial.suggest_int("alpha", HERO_WINRATE_DECAY_CONFIG["alpha"]["low"], HERO_WINRATE_DECAY_CONFIG["alpha"]["high"]),
            "beta": trial.suggest_int("beta", HERO_WINRATE_DECAY_CONFIG["beta"]["low"], HERO_WINRATE_DECAY_CONFIG["beta"]["high"]),
            "half_life_days": trial.suggest_categorical("half_life_days", HERO_WINRATE_DECAY_CONFIG["half_life_days"])
        }

        # 2. Generate features with suggested parameters
        hero_winrate_decay_features = self.hero_winrate_decay_generator.generate(self.sorted_match_list, **params)
        hero_winrate_decay_df = pd.DataFrame(instance.model_dump() for instance in hero_winrate_decay_features)

        # 3. Combine with other features and evaluate
        combined_df = merge_features_on_match_id([self.train_outcome_df, tuned_team_df, hero_winrate_decay_df, untuned_player_hero_df])
        y = combined_df['radiant_win']
        X = combined_df.drop(columns=['match_id', 'radiant_win'])
        
        time_series_cv = TimeSeriesSplit(n_splits=self.num_split)
        scores = cross_val_score(self.model, X, y, cv=time_series_cv, scoring=self.evaluation_metric, n_jobs=-1)
        
        return scores.mean()

    def _objective_tune_player_hero_features(self, trial: optuna.trial.Trial, tuned_team_df: pd.DataFrame, tuned_hero_df: pd.DataFrame) -> float:
        # 1. Suggest parameters for tuning
        params = {
            "player_credibility_C": trial.suggest_int("player_credibility_C", PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["player_credibility_C"]["low"], PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["player_credibility_C"]["high"]),
            "player_half_life_days": trial.suggest_categorical("player_half_life_days", PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["player_half_life_days"]),
            "hero_alpha": trial.suggest_int("hero_alpha", PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_alpha"]["low"], PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_alpha"]["high"]),
            "hero_beta": trial.suggest_int("hero_beta", PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_beta"]["low"], PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_beta"]["high"]),
            "hero_half_life_days": trial.suggest_categorical("hero_half_life_days", PLAYER_HERO_DYNAMIC_PRIOR_CONFIG["hero_half_life_days"])
        }
        
        # 2. Generate features with suggested parameters
        player_hero_features = self.player_hero_dynamic_prior_generator.generate(self.sorted_match_list, **params)
        player_hero_df = pd.DataFrame(instance.model_dump() for instance in player_hero_features)
        
        # 3. Combine with other features and evaluate
        combined_df = merge_features_on_match_id([self.train_outcome_df, tuned_team_df, tuned_hero_df, player_hero_df])
        y = combined_df['radiant_win']
        X = combined_df.drop(columns=['match_id', 'radiant_win'])
        
        time_series_cv = TimeSeriesSplit(n_splits=self.num_split)
        scores = cross_val_score(self.model, X, y, cv=time_series_cv, scoring=self.evaluation_metric, n_jobs=-1)
        
        return scores.mean()