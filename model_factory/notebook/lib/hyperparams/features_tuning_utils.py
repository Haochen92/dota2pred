from dota_oracle_common.models.features.schema import (
    FeatureHyperparams,
)
from lib.utils import merge_features_on_match_id
from typing import Set, Tuple, List
from dota_oracle_common.models.match import MatchTable
import pandas as pd

from dota_oracle_pipeline.feature_engineering.batch import (
    TeamDecayFeatureGenerator,
    HeroWinrateDecayFeatureGenerator,
    PlayerHeroDynamicPriorFeatureGenerator,
)

def create_train_test_from_params(
    match_list: List[MatchTable],
    features_hyperparams: FeatureHyperparams, 
    train_ids_set: Set[int], 
    test_ids_set: Set[int]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Creates train and test DataFrames from match data and feature hyperparameters.

    Args:
        match_list (List[MatchTable]): 
        features_hyperparams (FeatureHyperparams): 
        train_ids_set (Set[int]): 
        test_ids_set (Set[int]): 

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: train and test DataFrames
    """
    
    team_features_generator = TeamDecayFeatureGenerator()
    hero_features_generator = HeroWinrateDecayFeatureGenerator()
    player_hero_features_generator = PlayerHeroDynamicPriorFeatureGenerator()
    
    team_decay_features = team_features_generator.generate(
        match_list, 
        prior_count=features_hyperparams.team_features.prior_count, 
        prior_mean=features_hyperparams.team_features.prior_mean, 
        half_life_days=features_hyperparams.team_features.half_life_days
    )
    
    hero_winrate_decay_features = hero_features_generator.generate(
        match_list, 
        prior_count=features_hyperparams.hero_features.prior_count, 
        prior_mean=features_hyperparams.hero_features.prior_mean, 
        half_life_days=features_hyperparams.hero_features.half_life_days
    )
    
    player_hero_dynamic_prior_features = player_hero_features_generator.generate(
        match_list, 
        player_prior_count=features_hyperparams.player_hero_features.player_prior_count, 
        player_half_life_days=features_hyperparams.player_hero_features.player_half_life_days, 
        hero_half_life_days=features_hyperparams.player_hero_features.hero_half_life_days, 
        hero_prior_mean=features_hyperparams.player_hero_features.hero_prior_mean, 
        hero_prior_count=features_hyperparams.player_hero_features.hero_prior_count
    )
    
    team_decay_df = pd.DataFrame([feat.model_dump() for feat in team_decay_features])
    hero_winrate_decay_df = pd.DataFrame([feat.model_dump() for feat in hero_winrate_decay_features])
    player_hero_dynamic_prior_df = pd.DataFrame([feat.model_dump() for feat in player_hero_dynamic_prior_features])
    
    combined_df = merge_features_on_match_id([
        team_decay_df, 
        hero_winrate_decay_df, 
        player_hero_dynamic_prior_df
    ])
    
    train_features_df = combined_df[combined_df['match_id'].isin(train_ids_set)]
    test_features_df = combined_df[combined_df['match_id'].isin(test_ids_set)]
    
    return train_features_df, test_features_df
    