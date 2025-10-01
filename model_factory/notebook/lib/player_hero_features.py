import pandas as pd

def aggregate_player_win_rates(player_hero_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates player-hero win rates for Radiant and Dire teams.

    This function takes a DataFrame with individual player-hero win rates and adds
    three new columns:
    1. 'radiant_avg_player_wr': The average win rate of the 5 Radiant players.
    2. 'dire_avg_player_wr': The average win rate of the 5 Dire players.
    3. 'radiant_dire_wr_diff': The difference between the two averages.

    Args:
        player_hero_df: A DataFrame with 'match_id' and columns for player-hero
                        win rates (e.g., 'player_hero_0_win_rate', etc.).

    Returns:
        A new DataFrame with the three additional aggregate columns.
    """
    # Use .copy() to avoid modifying the original DataFrame (good practice)
    df = player_hero_df.copy()

    # 1. Define the column names for each team
    radiant_cols = [
        'player_hero_0_win_rate',
        'player_hero_1_win_rate',
        'player_hero_2_win_rate',
        'player_hero_3_win_rate',
        'player_hero_4_win_rate'
    ]
    dire_cols = [
        'player_hero_128_win_rate',
        'player_hero_129_win_rate',
        'player_hero_130_win_rate',
        'player_hero_131_win_rate',
        'player_hero_132_win_rate'
    ]
    
    # Ensure all required columns exist before proceeding
    required_cols = radiant_cols + dire_cols
    for col in required_cols:
        if col not in df.columns:
            raise KeyError(f"DataFrame is missing required column: '{col}'")

    # 2. Calculate the average win rate for each team across each row (axis=1)
    df['radiant_avg_player_wr'] = df[radiant_cols].mean(axis=1)
    df['dire_avg_player_wr'] = df[dire_cols].mean(axis=1)

    # 3. Calculate the difference between the team averages
    df['radiant_dire_player_hero_wr_diff'] = df['radiant_avg_player_wr'] - df['dire_avg_player_wr']

    return df