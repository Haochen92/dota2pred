import pandas as pd

# Constants
DRAFT_COLS = [
    '0_hero_id', '1_hero_id', '2_hero_id', '3_hero_id', '4_hero_id',
    '128_hero_id', '129_hero_id', '130_hero_id', '131_hero_id', '132_hero_id'
]
PLAYER_COLS = [
    '0_account_id', '1_account_id', '2_account_id', '3_account_id','4_account_id', 
    '128_account_id', '129_account_id', '130_account_id','131_account_id', '132_account_id'
]
LABEL_COL = 'radiant_win'
TIME_COL = 'start_time'
UUID_COL = 'match_id'


def extract_num(position):
    return position.split('_')[0]

def calculate_win_rate(matches):
    num_matches = len(matches)
    if num_matches == 0:
        return 0.5 # impute win_rate to 0.5 
    
    wins = ((matches['player_num'].apply(int) < 5) & matches[LABEL_COL]).sum()
    wins += ((matches['player_num'].apply(int) > 5) & ~matches[LABEL_COL]).sum()
    
    return wins/num_matches
        

def melt_df(df, value_vars, var_name, value_name):
    return pd.melt(df, 
                   id_vars=[TIME_COL, LABEL_COL, UUID_COL],
                   value_vars=value_vars, 
                   var_name=var_name, 
                   value_name=value_name)
    
def last_10_matches_winrate(df, current_date, account_id, hero_id):
    df_filtered = df[(df['account_id']==account_id) & 
                     (df['hero_id']==hero_id) & 
                     (df[TIME_COL] < current_date)].sort_values(
                         by=TIME_COL, ascending=False)
    
    return calculate_win_rate(df_filtered[:10])
    
    
def create_player_hero_features(input_df, limit_to=None):
    
    df = input_df.copy()
    
    df_melted_players = melt_df(df, PLAYER_COLS, 'player_position', 'account_id')
    df_melted_heros = melt_df(df, DRAFT_COLS, 'hero_position', 'hero_id')

    df_melted_players['player_num'] = df_melted_players['player_position'].apply(extract_num)
    df_melted_heros['hero_num'] = df_melted_heros['hero_position'].apply(extract_num)

    df_combined = pd.merge(df_melted_players, df_melted_heros, 
                       left_on=['start_time', 'radiant_win','match_id', 'player_num'], 
                       right_on=['start_time', 'radiant_win','match_id', 'hero_num'])

    df_combined = df_combined.sort_values(by='start_time', ascending=False)
    
    if limit_to:
        df_subset = df_combined.iloc[:limit_to*10]
    else:
        df_subset = df_combined
    
    # Calculate the rolling 10 win rates for each account_id hero_id combination 
    df_subset['win_rate'] = df_subset.apply(lambda row: last_10_matches_winrate(df_combined, row[TIME_COL], row['account_id'], row['hero_id']), axis=1)
  
    # Create the new columns 
    df_subset['player_hero_win_rate_col'] = df_subset['player_num'].astype(str) + '_account_ ' + df_subset['hero_num'].astype(str) + '_hero_win_rate'
    player_hero_feature = df_subset.pivot(index='match_id', columns='player_hero_win_rate_col', values='win_rate').reset_index().sort_values(by=UUID_COL, ascending=False)
    
    return player_hero_feature
    