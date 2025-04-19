from data_pipeline.fetching.api.steam_api import fetch_steam_data
from datetime import datetime as dt
from typing import List, Optional, Set, Any
import numpy as np 
import yaml
import asyncio
from src.config import ROOT_DIR
from src.pydantic_models import Match, LiveLeagueGames

# Constants
LIVE_LEAGUE_GAMES = 'IDOTA2Match_570/GetLiveLeagueGames/v1'
LEAGUE_IDS_FP = ROOT_DIR / 'constants' /'league_ids.yml'


# output file suffix
current_datetime = dt.now().strftime('%Y%m%d')

async def fetch_live_league_games() -> List[Optional[int]]:
    game_data = await fetch_steam_data(endpoint=LIVE_LEAGUE_GAMES)
    games = game_data['result']['games']
    league_ids = get_league_ids(LEAGUE_IDS_FP)
    
    live_league_games = populate_live_matches(games, league_ids)

    if not live_league_games:
        print("No premium or professional games right now")
        return []
    else: 
        return live_league_games    
         
def get_league_ids(file_path: str) -> Set[Any]:
    with open(file_path, 'r') as file:
        content = yaml.safe_load(file) or {}
        premium_leagues = content.get('PREMIUM_LEAGUES', {})
        professional_leagues = content.get('PROFESSIONAL_LEAGUES', {})
    
    return set(premium_leagues.values()) | set(professional_leagues.values())


def populate_live_matches(games: List[Any] = None, league_ids_set: Set[Any] = None):
    live_league_games = []

    for row in games:
        game_data = LiveLeagueGames(**row)
        league_id = game_data.league_id
        if league_id in league_ids_set:
            
            # Populate common fields
            match_data = {
                'match_id': game_data.match_id,
                'radiant_team_id': game_data.radiant_team.team_id,
                'radiant_name': game_data.radiant_team.team_name,
                'dire_team_id': game_data.dire_team.team_id,
                'dire_name': game_data.dire_team.team_name,
                'duration': game_data.scoreboard.duration,
                'start_time': int(dt.now().timestamp())
            }
            
            # Populate player data
            for team in ['radiant', 'dire']:
                faction = getattr(game_data.scoreboard, team)
                for player in faction.players:
                    slot = player.player_slot
                    player_data = {
                        f"slot_{slot}_account_id": player.account_id,
                        f"slot_{slot}_hero_id": player.hero_id
                    } 
                    match_data.update(player_data)
                    
            live_league_games.append(Match(**match_data))

        return live_league_games

if __name__ == '__main__':
    asyncio.run(fetch_live_league_games())