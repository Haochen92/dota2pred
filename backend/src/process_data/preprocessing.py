from src.utils.time_utils import unix_to_datetime

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
    """
    
    df = input_df.copy()
    
    # Select and order relevant columns
    selected_cols = DRAFT_COLS + PLAYER_COLS + TEAM_COL + [LABEL_COL, TIME_COL, UUID_COL]
    df = df[selected_cols]

    # Drop rows with any missing values
    df.dropna(inplace=True)

    # Convert Unix time to datetime format
    df[TIME_COL] = df[TIME_COL].apply(unix_to_datetime)

    # Drop duplicate matches
    df.drop_duplicates(subset=UUID_COL, inplace=True)

    # Sort dataframe by start time in descending order
    df.sort_values(by=TIME_COL, ascending=False, inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df

def process_label(df):
    label = df['radiant_win']
    label = label.apply(int)
    return label.values

def process_features(df):
    features = df.drop(columns=['start_time','radiant_win','match_id'])
    features = features.dropna()
    return features.values
