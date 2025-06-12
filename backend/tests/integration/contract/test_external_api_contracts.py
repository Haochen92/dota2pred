"""
Contract Testing - Verify external API mocks match real API responses.

This module tests that our mocked API responses match the actual structure 
and behavior of external APIs (Steam, OpenDota).
"""
import pytest
import aiohttp
import json
from unittest.mock import patch
from typing import Dict, Any

# import api endpoints
from dota_oracle.data_extraction import fetch_hero_data, fetch_league_data, fetch_live_league_games, fetch_pro_match, fetch_match_details
from dota_oracle.inference.model_inference_service import ModelInferenceService

# import pydantic api_models
from dota_oracle.models.heroes import HeroesAPIResponse
from dota_oracle.models.leagues import LeaguesAPIResponse
from dota_oracle.models.live_games import LiveLeagueAPIResponse
from dota_oracle.models.match import ProMatchAPIResponse, MatchesAPIResponse
from dota_oracle.models.inference import ModelMetaDataAPIResponse, ModelPredictionAPIResponse

pytestmark = [pytest.mark.asyncio, pytest.mark.contract]

async def test_heroes_api_contract():
    hero_data = await fetch_hero_data()
    
    assert isinstance(hero_data, dict), f"expected dictionary, got {type(hero_data.__name__)}"
    
    assert hero_data, "returned hero data should not be empty"
    

async def test_league_api_contract():
    list_league_item = await fetch_league_data()
    
    assert isinstance(list_league_item, list), f"expected list, got {type(list_league_item.__name__)}"
    
    assert list_league_item, "returned list_league_item data should not be empty"
    
    
async def test_live_league_contract():
    games_list = await fetch_live_league_games()
    
    assert isinstance(games_list, list), f"expected list, got {type(games_list.__name__)}"
    
    assert games_list, "returned games_list data should not be empty"
    
    
async def test_match_details_contract():
    valid_match_id = 8320876321
    
    match_details = await fetch_match_details(valid_match_id)
    
    assert isinstance(match_details, MatchesAPIResponse), f"expected type {MatchesAPIResponse.__name__}, got {type(match_details).__name__}"
    
    assert match_details
    
async def test_pro_match_contract():
    valid_max, valid_min = 8320876321 + 1, 8320876321
    
    pro_match_list = await fetch_pro_match(valid_max, valid_min)
    
    assert isinstance(pro_match_list, list), f"expect list, got {type(pro_match_list).__name__}"
    
    assert len(pro_match_list) == 1, f"expect 1 results, got {len(pro_match_list)}"
    