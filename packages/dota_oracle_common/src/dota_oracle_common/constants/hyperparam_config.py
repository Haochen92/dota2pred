from dota_oracle_common.models.features.schema import (
    TeamFeaturesHyperparams,
    PlayerHeroFeaturesHyperparams,
    HeroFeaturesHyperparams,
)

TEAM_FEATURES_HYPERPARAMS = TeamFeaturesHyperparams(prior_mean=0.52, prior_count=13, half_life_days=45)

HERO_FEATURES_HYPERPARAMS = HeroFeaturesHyperparams(prior_mean=0.5, prior_count=50, half_life_days=45)

PLAYER_HERO_FEATURES_HYPERPARAMS = PlayerHeroFeaturesHyperparams(
    player_prior_count=8, player_half_life_days=60, hero_prior_count=50, hero_prior_mean=0.5, hero_half_life_days=45
)

LOGISTIC_REGRESSION_HYPERPARAMS = {
    "C": 2752,
    "penalty": "l1",
}
