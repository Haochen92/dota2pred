import pandas as pd
from sklearn.preprocessing import MultiLabelBinarizer
from constants.constants import HERO_DICT
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text

async def get_transformed_features(engine: AsyncEngine, match_id: str) -> pd.DataFrame:
    hero_features = await transform_hero_features(engine, match_id)
    
    async with engine.connect() as conn:
        # For player_hero_features
        query = text("SELECT * FROM player_hero_features WHERE match_id = :match_id")
        result = await conn.execute(query, {"match_id": match_id})
        player_hero_features = pd.DataFrame(result.fetchall(), columns=result.keys())
        
        # For team_features
        query = text("SELECT * FROM team_features WHERE match_id = :match_id")
        result = await conn.execute(query, {"match_id": match_id})
        team_features = pd.DataFrame(result.fetchall(), columns=result.keys())
    
    combined_features = hero_features.merge(player_hero_features, on='match_id', how='inner')
    combined_features = combined_features.merge(team_features, on='match_id', how='inner')
    
    return combined_features

async def transform_hero_features(engine: AsyncEngine, match_id: str) -> pd.DataFrame:
    
    async with engine.connect() as conn:
        query = text("SELECT * FROM hero_features WHERE match_id = :match_id")
        result = await conn.execute(query, {"match_id": match_id})
        hero_features = pd.DataFrame(result.fetchall(), columns=result.keys())

    hero_dict = HERO_DICT
    ALL_HEROES = list(hero_dict.values())
    
    mlb = MultiLabelBinarizer(classes=ALL_HEROES)
    hero_matrix = mlb.fit_transform(hero_features['hero_picks'])
    features = pd.DataFrame(hero_matrix, columns=mlb.classes_)
    features.insert(0, 'match_id', hero_features['match_id'].values)
    return features