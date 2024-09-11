from datetime import datetime as dt
from src.config import ROOT_DIR
import yaml
import pandas as pd

# Constants
CONSTANTS_FILE_PATH = f'{ROOT_DIR}/constants/constants.yml'
DRAFT_COLS = [
    '0_hero_id', '1_hero_id', '2_hero_id', '3_hero_id', '4_hero_id',
    '128_hero_id', '129_hero_id', '130_hero_id', '131_hero_id', '132_hero_id'
]
LABEL_COL = 'radiant_win'
TIME_COL = 'start_time'
UUID_COL = 'match_id'

def load_constants():
    try:
        with open(CONSTANTS_FILE_PATH, 'r') as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        raise FileNotFoundError(f"'{CONSTANTS_FILE_PATH}' does not exist!")

def get_heroes_constants(data):
    hero_dict = data.get('HEROES_CONSTANTS', {})
    if not hero_dict or not isinstance(hero_dict, dict):
        raise ValueError("Unable to load hero constants or they are not in a valid format.")
    return hero_dict

def create_hero_level_features(input_df, limit_to=None):
    data = load_constants()
    hero_dict = get_heroes_constants(data)
    
    # create a copy of the df so the original won't be modified
    df = input_df.copy()
        
    # Mapping hero IDs to their respective names
    df[DRAFT_COLS] = df[DRAFT_COLS].applymap(hero_dict.get)
    
    df_melted_heroes = pd.melt(df, id_vars=[TIME_COL, LABEL_COL, UUID_COL],
                               value_vars=DRAFT_COLS, 
                               var_name='hero_position',
                               value_name='hero_name')
    
    df_encoded = pd.concat([df_melted_heroes, pd.get_dummies(df_melted_heroes['hero_name'])], axis=1)
    df_encoded = df_encoded.groupby([UUID_COL]).sum(numeric_only=True).reset_index()

    cols_to_merge = [TIME_COL, LABEL_COL, UUID_COL]
    
    heroes_features = df_encoded.merge(df[cols_to_merge].drop_duplicates(), on=UUID_COL, how='left').sort_values(by=UUID_COL, ascending=False)  
    
    if limit_to:
        return heroes_features.iloc[:limit_to]
    else:
        return heroes_features       
