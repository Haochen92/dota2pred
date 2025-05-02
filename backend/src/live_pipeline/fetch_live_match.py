from typing import Dict, Any
from data_pipeline.fetching.fetch_live_leagues import fetch_live_league_games

async def get_current_matches() -> Dict[int, Dict[str, Any]]:
    res = await fetch_live_league_games()
    if not res:
        return {}
    
    return {match.match_id: match.model_dump() for match in res }