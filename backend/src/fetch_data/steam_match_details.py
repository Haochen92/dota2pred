import requests
import pandas as pd
import numpy as np
from retry import retry
from sqlalchemy.engine import create_engine, URL
import psycopg2
from datetime import datetime 
from pathlib import Path

# Get the current date in YYYYMMDD format
current_date = datetime.now().strftime('%Y%m%d')

# Define paths
root_path = Path(__file__).resolve().parents[1]  # This points to the root directory
input_file_path = root_path / 'data' / f'dota2_pro_match_ids_{current_date}.csv'

# Constants
STEAM_URL = 'http://api.steampowered.com/'
API_KEY = 'F0E5D7D11B592792FE20D84FBB745D97'
DATABASE_CREDENTIALS = {
    "username": 'liuhaochen',
    "host": 'localhost',
    "port": '5432',
    "database": 'test'
}

# Initial configurations
session = requests.Session()
session.params.update({'key': API_KEY})


@retry(tries=3, delay=2)
def get_response(match_id):
    url = f'{STEAM_URL}IDOTA2Match_570/GetMatchDetails/v1?match_id={match_id}'
    print(f'Requesting... {url}')
    try:
        res = session.get(url)
        if res.status_code == 200:
            print("API endpoint is valid")
        else:
            print("Status Code is:", res.status_code)
        match_details = res.json()
        if not match_details:
            raise ValueError(f"Empty dictionary for match_id {match_id}")
        return match_details
    except requests.exceptions.RequestException as e:
        print(f"An error occured: {e}")
        return None
    
    


def pro_match_template():
    template = {
        'match_id': np.nan,
        'radiant_team_id': np.nan,
        'radiant_name': np.nan,
        'dire_team_id': np.nan,
        'dire_name': np.nan,
        'duration': np.nan,
        'start_time': np.nan,
        'radiant_win': np.nan
    }
    for i in list(range(0, 5)) + list(range(128, 133)):
        template[f"{i}_account_id"] = np.nan
        template[f"{i}_hero_id"] = np.nan
    return template


def extract_data_from_match_records(records):
    matches = []
    for row in records:
        match_dict = pro_match_template()
        result = row.get('result', {})
        if result:
            populate_data_to_dict(match_dict, result)
        matches.append(match_dict)
    return matches


def populate_data_to_dict(dictionary, result):
    dictionary.update({
        'match_id': result.get('match_id', np.nan),
        'radiant_team_id': result.get('radiant_team_id', np.nan),
        'radiant_name': result.get('radiant_name', np.nan),
        'dire_team_id': result.get('dire_team_id', np.nan),
        'dire_name': result.get('dire_name', np.nan),
        'duration': result.get('duration', np.nan),
        'start_time': result.get('start_time', np.nan),
        'radiant_win': result.get('radiant_win', np.nan)
    })
    for player in result.get('players', {}):
        slot = player.get('player_slot')
        if slot is not None:
            dictionary[f"{slot}_account_id"] = player.get('account_id', np.nan)
            dictionary[f"{slot}_hero_id"] = player.get('hero_id', np.nan)

def fetch_match_details(match_ids):
    match_records = []
    for match_id in match_ids:
        try:
            match_data = get_response(match_id)
            match_records.append(match_data)
        except Exception:
            print(f"Failed to fetch data for match_id {match_id} after multiple retries.")

    list_matches = extract_data_from_match_records(match_records)
    return pd.DataFrame(list_matches)
    

def main():
    with open(input_file_path, 'r') as file:
        df = pd.read_csv(file)
    match_ids = df['match_id']

    df_pro_matches = fetch_match_details(match_ids)

    url_object = URL.create("postgresql+psycopg2", **DATABASE_CREDENTIALS)
    engine = create_engine(url_object)
    df_pro_matches.to_sql('pro_matches', engine, index=False, if_exists='append')


if __name__ == '__main__':
    main()
