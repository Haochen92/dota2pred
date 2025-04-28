from typing import List
from src.pydantic_models.live_league_games import LiveLeagueGame
from src.pydantic_models.match import Match
from utils.set_logging import get_logger

logger = get_logger(__name__)

def parse_live_league_games(live_games: List[LiveLeagueGame]) -> List[Match]:
    live_league_games = []

    for row in live_games:
        try:
            # Populate common fields
            match_data = {
                'match_id': row.match_id,
                'radiant_team_id': row.radiant_team.team_id,
                'radiant_name': row.radiant_team.team_name,
                'dire_team_id': row.dire_team.team_id,
                'dire_name': row.dire_team.team_name,
                'duration': row.scoreboard.duration,
                'start_time': row.start_time
            }
            
            # Populate player data
            for team in ['radiant', 'dire']:
                faction = getattr(row.scoreboard, team)
                for player in faction.players:
                    slot = player.player_slot
                    player_data = {
                        f"slot_{slot}_account_id": player.account_id,
                        f"slot_{slot}_hero_id": player.hero_id
                    } 
                    match_data.update(player_data)
                    
            live_league_games.append(Match(**match_data))
        except Exception as e:
            # This catches all validation errors, attribute errors, etc
            logger.info(f"Skipping match {row['match_id']} due to error: {str(e)}")
            continue

    return live_league_games