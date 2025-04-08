import pandas as pd
from src.postgresql import get_engine
from sklearn.preprocessing import MultiLabelBinarizer
from constants.constants import HERO_DICT

def transform_hero_features():
    engine = get_engine()
    
    hero_features = pd.read_sql(
    "SELECT * FROM hero_features",
    con=engine
    )

    hero_dict = HERO_DICT
    ALL_HEROES = list(hero_dict.values())
    
    mlb = MultiLabelBinarizer(classes=ALL_HEROES)
    hero_matrix = mlb.fit_transform(hero_features['hero_picks'])
    features = pd.DataFrame(hero_matrix, columns=mlb.classes_)
    features.insert(0, 'match_id', hero_features['match_id'].values)
    
    return features