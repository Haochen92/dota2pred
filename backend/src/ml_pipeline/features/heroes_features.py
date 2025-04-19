from sqlmodel import Session
import pandas as pd
from database.schemas.features import HeroFeatures
from src.postgresql import get_engine

DRAFT_COLS = [
    '0_hero_id', '1_hero_id', '2_hero_id', '3_hero_id', '4_hero_id',
    '128_hero_id', '129_hero_id', '130_hero_id', '131_hero_id', '132_hero_id'
]

def create_hero_features(input_df: pd.DataFrame) -> pd.DataFrame:
    
    df = input_df.copy()
    hero_features = df[[*DRAFT_COLS, 'match_id']]
    
    return hero_features

def store_to_db(hero_features):
    engine = get_engine()
    with Session(engine) as session:
        for _, row in hero_features.iterrows():
            # Filter the row data to only include fields in the model
            # Convert to dict first to make it easier to filter
            row_dict = dict(row)
            match_id = row_dict['match_id']
            hero_picks = []
            
            for column, value in row_dict.items():
                if column in DRAFT_COLS:
                    hero_picks.append(value)
                    
            hero_features = HeroFeatures(
                match_id=match_id,
                hero_picks=hero_picks
            )
            
            session.merge(hero_features)
        
        session.commit()
        
def create_and_store_hero_features(input_df):
    features = create_hero_features(input_df)
    store_to_db(features)
    
    return features
    
    