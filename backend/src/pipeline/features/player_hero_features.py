import pandas as pd
from sqlmodel import Session
from database.schemas.features import PlayerHeroFeature
from src.postgresql import get_engine

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

def create_player_hero_features(df):
    
    df_melted_players = df_melted_players = pd.melt(df.copy(), id_vars=['start_time','radiant_win','match_id'],
                            value_vars=PLAYER_COLS, 
                            var_name='player_position',
                            value_name='account_id')

    df_melted_heroes = pd.melt(df.copy(), id_vars=['start_time','radiant_win','match_id'],
                            value_vars=DRAFT_COLS,
                            var_name='hero_position',
                            value_name='hero_name')
    
    df_melted_players['player_num'] = df_melted_players['player_position'].apply(lambda x: x.split('_')[0])
    df_melted_heroes['hero_num'] = df_melted_heroes['hero_position'].apply(lambda x: x.split('_')[0])

    df_combined = pd.merge(df_melted_players, df_melted_heroes, 
                       left_on=['start_time', 'radiant_win','match_id', 'player_num'], 
                       right_on=['start_time', 'radiant_win','match_id', 'hero_num'])

    df_combined = df_combined.sort_values(by='start_time', ascending=False)
    
    # 2. Determine if a player won based on their position and match outcome
    df_combined['player_won'] = ((df_combined['player_num'].astype(int) < 5) & df_combined['radiant_win']) | \
                           ((df_combined['player_num'].astype(int) >= 5) & ~df_combined['radiant_win'])
                           
    # 2. Create a key for each account_id and hero combination
    # Use hero_name to identify unique heroes
    df_combined['account_hero_key'] = df_combined['account_id'].astype(str) + '_' + df_combined['hero_name'].astype(str)
    
    # 3. Sort data chronologically
    df_sorted = df_combined.sort_values(by=TIME_COL)
    
    win_rates = {}
    for key, group in df_sorted.groupby('account_hero_key'):
        for i, row in group.iterrows():
            match_id = row['match_id']
            player_num = row['player_num']
            current_time = row[TIME_COL]
            
            # Find previous matches for this player-hero combo
            previous_matches = group[group[TIME_COL] < current_time]
            
            # Calculate win rate from previous matches
            if len(previous_matches) > 0:
                previous_10 = previous_matches.sort_values(by=TIME_COL, ascending=False).head(10)
                win_rate = previous_10['player_won'].mean()
            else:
                win_rate = 0.5
                
            win_rates[(match_id, player_num)] = win_rate
        
    # 5. Apply calculated win rates to dataframe
    df_combined['win_rate'] = df_combined.apply(
        lambda row: win_rates.get((row['match_id'], row['player_num']), 0.5),
        axis=1
    )
    
    # 6. Create column names based on player and hero positions
    df_combined['player_hero_win_rate_col'] = (
        'player_hero_' + df_combined['player_num'].astype(str) + '_win_rate'
    )
    
    # 7. Create final pivot table with position-based columns
    player_hero_features = df_combined.pivot(
        index='match_id', 
        columns='player_hero_win_rate_col', 
        values='win_rate'
    ).reset_index()
    
    return player_hero_features
    
            
def store_to_db(player_hero_feature):
    
    engine = get_engine()
    records = player_hero_feature.to_dict(orient="records")
    
    with Session(engine) as session:
        # For each match record
        for record in records:
            # Create a new PlayerHeroFeature instance
            player_hero_feature_obj = PlayerHeroFeature(
                match_id=record["match_id"],
                player_hero_0_win_rate=record["player_hero_0_win_rate"],
                player_hero_1_win_rate=record["player_hero_1_win_rate"],
                player_hero_2_win_rate=record["player_hero_2_win_rate"], 
                player_hero_3_win_rate=record["player_hero_3_win_rate"],
                player_hero_4_win_rate=record["player_hero_4_win_rate"],
                player_hero_128_win_rate=record["player_hero_128_win_rate"],
                player_hero_129_win_rate=record["player_hero_129_win_rate"],
                player_hero_130_win_rate=record["player_hero_130_win_rate"],
                player_hero_131_win_rate=record["player_hero_131_win_rate"],
                player_hero_132_win_rate=record["player_hero_132_win_rate"]
            )
            
            # Use merge instead of add
            session.merge(player_hero_feature_obj)
        
            # Commit all records at once
            try:
                session.commit()
                print(f"Successfully stored {len(records)} player-hero feature records")
            except Exception as e:
                session.rollback()
                print(f"Error storing player-hero features: {str(e)}")

    
    def create_and_store_player_hero_features(df):
        features = create_player_hero_features(df)
        store_to_db(features)