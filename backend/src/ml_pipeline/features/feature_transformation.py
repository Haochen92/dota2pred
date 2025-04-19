import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from constants.constants import HERO_DICT

def get_transformed_features(engine, match_id):
    hero_features = transform_hero_features(engine, match_id)
    player_hero_features = pd.read_sql(
        "SELECT * FROM player_hero_features WHERE match_id = :match_id",
        con=engine,
        params={"match_id": match_id}
    )
    team_features = pd.read_sql(
        "SELECT * FROM team_features WHERE match_id = :match_id",
        con=engine,
        params={"match_id": match_id}
    )
    
    combined_features = hero_features.merge(player_hero_features, on='match_id', how='inner')
    combined_features = combined_features.merge(team_features, on='match_id', how='inner')
    
    return combined_features

def transform_hero_features(engine, match_id: str):
    
    hero_features = pd.read_sql(
        "SELECT * FROM hero_features WHERE match_id = :match_id",
        con=engine,
        params={"match_id": match_id}
    )

    hero_dict = HERO_DICT
    ALL_HEROES = list(hero_dict.values())
    
    mlb = MultiLabelBinarizer(classes=ALL_HEROES)
    hero_matrix = mlb.fit_transform(hero_features['hero_picks'])
    features = pd.DataFrame(hero_matrix, columns=mlb.classes_)
    features.insert(0, 'match_id', hero_features['match_id'].values)
    
    return features