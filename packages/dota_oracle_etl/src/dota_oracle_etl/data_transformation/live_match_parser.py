from typing import List
from dota_oracle_common.models.live_games.schema import OngoingLeagueGame
from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.time_utils import to_utc_datetime_object
from dota_oracle_common.data_repository.heroes_repository import HeroesRepository

logger = get_logger(__name__)

async def parse_live_league_games(raw_live_games: List[OngoingLeagueGame], hero_repo: HeroesRepository) -> List[MatchTable]:
    parsed_live_league_games = []
    
    hero_map = await hero_repo.get_hero_id_map()

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
                    mapped_hero_id = hero_map.get(player.hero_id, None) 
                    if not mapped_hero_id:
                        logger.warning(f"Missing hero_map for hero_id: {player.hero_id}")
                    player_data = {
                        f"slot_{slot}_account_id": player.account_id,
                        f"slot_{slot}_hero_id": mapped_hero_id
                    } 
                    match_data.update(player_data)
                    
            parsed_live_league_games.append(MatchTable(**match_data))
        except Exception as e:
            logger.info(f"Skipping match {row.match_id} due to error: {str(e)}")
            continue

    return parsed_live_league_games