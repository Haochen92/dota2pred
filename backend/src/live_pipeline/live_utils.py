# Refactor to fetch from database instead. 

async def get_league_ids(file_path: str) -> Set[int]:
    with open(file_path, 'r') as file:
        content = yaml.safe_load(file) or {}
        premium_leagues = content.get('PREMIUM_LEAGUES', {})
        professional_leagues = content.get('PROFESSIONAL_LEAGUES', {})
    
    return set(premium_leagues.values()) | set(professional_leagues.values())