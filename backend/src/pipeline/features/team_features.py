from collections import deque
from sqlmodel import Session
from database.schemas.features import TeamFeatures
from src.postgresql import get_engine

def calculate_win_rate(team_histories: list, team_name: str) -> float:
    if not team_histories:
        return 0.5
    
    win = 0
    for match in team_histories:
        if match['radiant_name'] == team_name and match['radiant_win']:
            win += 1
        elif match['dire_name'] == team_name and not match['radiant_win']:
            win += 1
        
    return win/ len(team_histories)

def update_team_history(team_histories, radiant, dire, match):
    if radiant not in team_histories:
        team_histories[radiant] = deque(maxlen=10)
    if dire not in team_histories:
        team_histories[dire] = deque(maxlen=10)
        
    team_histories[radiant].append(match)
    team_histories[dire].append(match)
    
def update_matchup_history(matchup_histories, radiant, dire, match):
    if (radiant, dire) not in matchup_histories:
        matchup_histories[(radiant, dire)] = deque(maxlen=10)
    
    matchup_histories[(radiant,dire)].append(match)
    
def calculate_matchup(matchup_histories: list, team_name:str) -> float:
    if not matchup_histories:
        return 0.5
    
    win = 0
    for match in matchup_histories:
        if match['radiant_name'] == team_name and match['radiant_win']:
            win += 1
        elif match['dire_name'] == team_name and not match['radiant_win']:
            win += 1
    
    return win / len(matchup_histories)

def create_team_features(df):
    team_histories = {}
    matchup_histories = {}
    team_level_features = []

    for _, match in df.iterrows():
        radiant_team = match['radiant_name']
        dire_team = match['dire_name']
        
        # Calculate features for each row
        radiant_win_rate = calculate_win_rate(team_histories.get(radiant_team, []), radiant_team)
        dire_win_rate = calculate_win_rate(team_histories.get(dire_team, []), dire_team)
        
        all_matches = list(matchup_histories.get((radiant_team, dire_team), [])) \
                        + list(matchup_histories.get((dire_team, radiant_team), []))
        matchup_rate = calculate_matchup(all_matches, radiant_team)
        
        # append features to results
        team_level_features.append({
            'match_id': match['match_id'],
            'radiant_win_rate': radiant_win_rate,
            'dire_win_rate': dire_win_rate,
            'radiant_dire_matchup': matchup_rate
        })
        
        # update history dictionaries
        update_team_history(team_histories, radiant_team, dire_team, match)
        update_matchup_history(matchup_histories, radiant_team, dire_team, match)
        
        
    return team_level_features

def store_to_db(features):
    model_fields = {
        name for name, field in TeamFeatures.__fields__.items()
        if not name.startswith('_')
    }
    
    engine = get_engine()
    
    with Session(engine) as session:
        for row in features:
            # 'row' is a pandas Series, which works similarly to a dictionary
            filtered_data = {
                field: row[field]
                for field in model_fields
                if field in row
            }
            
            # Create the model instance with the filtered data
            team_features = TeamFeatures(**filtered_data)
            session.merge(team_features)
    
        session.commit()
        
def create_and_store_team_features(df):
    features = create_team_features()
    store_to_db(features)