label_col = 'radiant_win'
time_col = 'start_time'
uuid_col = 'match_id'


def _get_last_10_matches(df, conditions, current_date):
    return df[conditions & (df[time_col] < current_date )].tail(10)

def _calculate_win_rate(matches, team_name):
    if len(matches) == 0:
        return 0.5  # Impute value for debut match
    wins = ((matches['radiant_name'] == team_name) & matches[label_col]).sum()
    wins += ((matches['dire_name'] == team_name) & ~matches[label_col]).sum()
    return wins / len(matches)

def last_10_matches_win_rate(df, team_name, current_date):
    conditions = (df['radiant_name'] == team_name) | (df['dire_name'] == team_name)
    matches = _get_last_10_matches(df, conditions, current_date)
    return _calculate_win_rate(matches, team_name)


def radiant_dire_matchup(df, radiant_name, dire_name, current_date):
    conditions = (
        ((df['radiant_name'] == radiant_name) & (df['dire_name'] == dire_name)) |
        ((df['dire_name'] == radiant_name) & (df['radiant_name'] == dire_name))
    )
    matches = _get_last_10_matches(df, conditions, current_date)
    return _calculate_win_rate(matches, radiant_name)


def create_team_level_features(df, limit_to=None):
    
    required_columns = ['radiant_name', 'dire_name', time_col, label_col, uuid_col]
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"The DataFrame is missing some of the required columns: {required_columns}")
    
    if limit_to:
        subset_df = df.iloc[:limit_to].copy()
    else:
        subset_df = df.copy()
    
    subset_df['radiant_win_rate'] = subset_df.apply(lambda row: last_10_matches_win_rate(df, row['radiant_name'], row['start_time']), axis=1)
    subset_df['dire_win_rate'] = subset_df.apply(lambda row: last_10_matches_win_rate(df, row['dire_name'], row['start_time']), axis=1)
    subset_df['radiant_dire_matchup'] = subset_df.apply(lambda row: radiant_dire_matchup(df, row['radiant_name'], row['dire_name'], row['start_time']), axis=1)

    team_features = subset_df[['radiant_dire_matchup', 'radiant_win_rate', 'dire_win_rate', label_col, time_col, uuid_col]]
    
    return team_features
    