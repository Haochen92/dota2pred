from pydantic_models.match import Match
import random
from typing import List, Optional

def generate_mock_matches(count: int = 1, 
                          missing_heroes: bool = False,
                          missing_players: bool = False,
                          missing_teams: bool = False) -> List[Match]:
    """
    Generate mock Match objects with configurable constraints.
    
    Args:
        count: Number of match objects to generate
        missing_heroes: If True, some hero IDs will be None
        missing_players: If True, some player account IDs will be None
        missing_teams: If True, some team IDs will be None
    
    Returns:
        List of Match objects with randomized data
    """
    matches = []
    
    team_names = ["Team Secret", "Team Liquid", "OG", "Evil Geniuses", 
                  "Virtus.pro", "PSG.LGD", "Fnatic", "Alliance"]
    
    team_ids = [1838315, 2163, 2586976, 39, 1883502, 15, 350190, 111474]
    
    for i in range(count):
        # Basic match data
        match_id = random.randint(10000, 99999) + i
        start_time = 1650000000 + random.randint(0, 999999)
        duration = random.uniform(0, 5000)
        
        # Team data
        radiant_idx = random.randint(0, len(team_names)-1)
        dire_idx = random.randint(0, len(team_names)-1)
        while dire_idx == radiant_idx:  # Ensure different teams
            dire_idx = random.randint(0, len(team_names)-1)
            
        radiant_name = None if missing_teams else team_names[radiant_idx]
        radiant_team_id = None if missing_teams else team_ids[radiant_idx]
        dire_name = None if missing_teams else team_names[dire_idx]
        dire_team_id = None if missing_teams else team_ids[dire_idx]
        
        # Create match with basic data
        match_data = {
            "match_id": match_id,
            "radiant_name": radiant_name,
            "radiant_team_id": radiant_team_id,
            "dire_name": dire_name,
            "dire_team_id": dire_team_id,
            "start_time": start_time,
            "duration": duration,
            "radiant_win": random.choice([True, False, None])
        }
        
        # Add hero IDs
        for slot in range(5):
            if not missing_heroes or random.random() > 0.3:
                match_data[f"slot_{slot}_hero_id"] = random.randint(1, 130)
                
        for slot in range(128, 133):
            if not missing_heroes or random.random() > 0.3:
                match_data[f"slot_{slot}_hero_id"] = random.randint(1, 130)
                
        # Add player account IDs
        for slot in range(5):
            if not missing_players or random.random() > 0.3:
                match_data[f"slot_{slot}_account_id"] = random.randint(100000, 999999)
                
        for slot in range(128, 133):
            if not missing_players or random.random() > 0.3:
                match_data[f"slot_{slot}_account_id"] = random.randint(100000, 999999)
                
        matches.append(Match(**match_data))
        
    return matches

# Generate different test scenarios
MOCK_LIVE_MATCHES_ONE = generate_mock_matches(1)
MOCK_LIVE_MATCHES_TWO = generate_mock_matches(2)
MOCK_LIVE_MATCHES_THREE = generate_mock_matches(1, missing_heroes=True, missing_players=True)
MOCK_LIVE_MATCHES_FOUR = generate_mock_matches(2, missing_teams=True)

# For specific testing needs, generate custom datasets
matches_with_no_duration = generate_mock_matches(1)
matches_with_no_duration[0].duration = 0.0

# For reproducible tests, you can set a seed
# random.seed(42)