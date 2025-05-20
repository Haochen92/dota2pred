from typing import List
from dota_oracle.pydantic_models.live_league_games import LiveLeagueGame
from dota_oracle.pydantic_models.match import Match
from dota_oracle.utils.set_logging import get_logger
from dota_oracle.utils.time_utils import to_utc_datetime_object
from dota_oracle.data_repository.heroes_repository import HeroesRepository

logger = get_logger(__name__)

async def parse_live_league_games(raw_live_games: List[LiveLeagueGame], hero_repo: HeroesRepository) -> List[Match]:
    parsed_live_league_games = []
    
    try:
        hero_map = await hero_repo.get_hero_id_map()
    except Exception as e:
        raise e

    for row in raw_live_games:
        try:
            # Populate common fields
            match_data = {
                'match_id': row.match_id,
                'radiant_team_id': row.radiant_team.team_id,
                'radiant_name': row.radiant_team.team_name,
                'dire_team_id': row.dire_team.team_id,
                'dire_name': row.dire_team.team_name,
                'duration': row.scoreboard.duration,
                'start_time': to_utc_datetime_object(row.start_time)
            }
            
            # Populate player data
            for team in ['radiant', 'dire']:
                faction = getattr(row.scoreboard, team)
                for player in faction.players:
                    slot = player.player_slot
                    mapped_hero_id = hero_map.get(player.hero_id, "unknown hero")
                    player_data = {
                        f"slot_{slot}_account_id": player.account_id,
                        f"slot_{slot}_hero_id": mapped_hero_id
                    } 
                    match_data.update(player_data)
                    
            parsed_live_league_games.append(Match(**match_data))
        except Exception as e:
            logger.info(f"Skipping match {row.match_id} due to error: {str(e)}")
            continue

    return parsed_live_league_games