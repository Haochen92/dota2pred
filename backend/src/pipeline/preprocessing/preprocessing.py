import pandas as pd

# Constants
DRAFT_COLS = [
    '0_hero_id', '1_hero_id', '2_hero_id', '3_hero_id', '4_hero_id',
    '128_hero_id', '129_hero_id', '130_hero_id', '131_hero_id', '132_hero_id'
]
PLAYER_COLS = [
    '0_account_id', '1_account_id', '2_account_id', '3_account_id', '4_account_id',
    '128_account_id', '129_account_id', '130_account_id', '131_account_id', '132_account_id'
]
TEAM_COL = ['radiant_name','dire_name']
LABEL_COL = 'radiant_win'
TIME_COL = 'start_time'
UUID_COL = 'match_id'


def preprocess_df(input_df):
    """
    Preprocesses the given dataframe based on certain feature columns, 
    removing duplicates and converting unix time to datetime.
    
    Args:
        input_df: Input DataFrame containing the raw data
        
    Returns:
        Preprocessed DataFrame with selected columns, duplicates removed, 
        and time converted to datetime
    """
    # Check if all required columns exist
    required_cols = DRAFT_COLS + PLAYER_COLS + TEAM_COL + [LABEL_COL, TIME_COL, UUID_COL]
    missing_cols = [col for col in required_cols if col not in input_df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Create a smaller copy 
    df = input_df[required_cols].copy()
    
    # Count and log number of rows with NaN values
    nan_count = df.isna().any(axis=1).sum()
    if nan_count > 0:
        print(f"Removing {nan_count} rows with missing values")
    
    # Drop rows with any missing values
    df = df.dropna()
    
    # Convert Unix time to datetime format
    df[TIME_COL] = pd.to_datetime(df[TIME_COL], unit='s')
    
    # Count duplicates before removing them
    duplicate_count = df.duplicated(subset=UUID_COL).sum()
    if duplicate_count > 0:
        print(f"Removing {duplicate_count} duplicate matches")
    
    # Drop duplicate matches
    df = df.drop_duplicates(subset=UUID_COL)
    
    # Sort dataframe, starting with oldest match
    df = df.sort_values(by=TIME_COL).reset_index(drop=True)
    
    return df

def process_label(df):
    label = df['radiant_win']
    label = label.apply(int)
    return label.values

def process_features(df):
    features = df.drop(columns=['start_time','radiant_win','match_id'])
    features = features.dropna()
    return features.values
