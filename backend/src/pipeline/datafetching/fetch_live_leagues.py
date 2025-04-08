import requests
import pandas as pd
from datetime import datetime as dt
import numpy as np
import yaml
from retry import retry
from src.config import ROOT_DIR

# Constants
STEAM_URL = 'http://api.steampowered.com/'
LIVE_LEAGUE_GAMES = 'IDOTA2Match_570/GetLiveLeagueGames/v1'
API_KEY = 'F0E5D7D11B592792FE20D84FBB745D97'
LEAGUE_IDS_FILE = ROOT_DIR / 'constants' /'league_ids.yml'

# Setup request session for Steam API
session = requests.Session()
session.params.update({'key': API_KEY})

# output file suffix
current_datetime = dt.now().strftime('%Y%m%d')
output_fp = f'{ROOT_DIR}/data/df_live_{current_datetime}.csv'

@retry(tries=3, delay=2)
def fetch_live_league_games():
    url = f'{STEAM_URL}{LIVE_LEAGUE_GAMES}'
    response = session.get(url)
    response_json = response.json()
    
    if not response_json:
        raise ValueError("Empty dictionary, retrying...")
    
    return response_json

def get_league_ids(file_path):
    with open(file_path, 'r') as file:
        content = yaml.safe_load(file) or {}
        premium_leagues = content.get('PREMIUM_LEAGUES', {})
        professional_leagues = content.get('PROFESSIONAL_LEAGUES', {})
    
    return list(premium_leagues.values()), list(professional_leagues.values())

def live_match_template():
    template = {
        'match_id': np.nan,
        'radiant_team_id': np.nan,
        'radiant_name': np.nan,
        'dire_team_id': np.nan,
        'dire_name': np.nan,
        'game_duration': 0,
        'start_time': 0,
        'radiant_win': -1
    }
    
    for i in list(range(0, 5)) + list(range(128, 133)):
        template[f"{i}_account_id"] = np.nan
        template[f"{i}_hero_id"] = np.nan
    
    return template

def populate_live_matches(games, premium_list, professional_list):
    live_league_games = []

    for row in games:
        league_id = row.get('league_id')
        if league_id in premium_list + professional_list:
            match = live_match_template()
            match.update({
                'league_id': league_id,
                'match_id': row.get('match_id', np.nan),
                'radiant_team_id': row.get('radiant_team', {}).get('team_id', np.nan),
                'radiant_name': row.get('radiant_team', {}).get('team_name', np.nan),
                'dire_team_id': row.get('dire_team', {}).get('team_id', np.nan),
                'dire_name': row.get('dire_team', {}).get('team_name', np.nan),
                'game_duration': row.get('scoreboard', {}).get('duration', np.nan),
                'start_time': dt.now().timestamp()
            })

            for team in ['radiant', 'dire']:
                for player in row.get('scoreboard', {}).get(team, {}).get('players', []):
                    slot = player.get('player_slot')
                    if slot is not None:
                        match.update({
                            f"{slot}_account_id": player.get('account_id', np.nan),
                            f"{slot}_hero_id": player.get('hero_id', np.nan)
                        })

            live_league_games.append(match)

    return live_league_games

def retrieve_live_league_games():
    game_data = fetch_live_league_games()
    games = game_data['result']['games']

    premium_list, professional_list = get_league_ids(LEAGUE_IDS_FILE)
    live_league_games = populate_live_matches(games, premium_list, professional_list)

    if not live_league_games:
        print("No premium or professional games right now")
    else:
        # pd.DataFrame(live_league_games).to_csv(output_fp, index=False)    
        return live_league_games    
         

if __name__ == '__main__':
    retrieve_live_league_games()