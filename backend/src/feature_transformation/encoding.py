from sklearn.preprocessing import MultiLabelBinarizer
from data_repository.heroes_repository import HeroesRepository
import pandas as pd


async def encode_hero_features(hero_features: pd.DataFrame, heros_repo: HeroesRepository) -> pd.DataFrame:
    
    if hero_features.empty:
        raise ValueError("Input dataframe is empty")
    
    if 'hero_picks' not in hero_features.columns:
        raise ValueError("missing column hero_picks")
    
    hero_map = await heros_repo.get_hero_id_map()
    if not hero_map:
        raise ValueError("HERO MAP object is empty")
    
    hero_classes = hero_map.values()
    
    # for some reason mlb requires explicit conversion of view object to list
    mlb = MultiLabelBinarizer(classes=list(hero_classes)) 
    
    hero_matrix = mlb.fit_transform(hero_features['hero_picks'])
    
    features = pd.DataFrame(
        hero_matrix,
        columns=mlb.classes_,
        index=hero_features.index 
    )
    
    features = features.assign(match_id=hero_features['match_id'])
    return features