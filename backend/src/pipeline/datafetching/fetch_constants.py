from prefect import flow, task 
from .opendota_api import get_opendota_df
from src.config import ROOT_DIR
import pandas as pd
import numpy as np
import yaml
import asyncio

league_constants_fpth = ROOT_DIR / "constants"/ "league_ids.yml"
hero_constants_fpth = ROOT_DIR / "constants" / "constants.yml"

@task 
async def fetch_league_ids():
    
    leagues = await get_opendota_df('leagues')
    
    # Filter and sort leagues
    premium_leagues = leagues[leagues['tier']=='premium'].sort_values(by='leagueid', ascending=False)
    professional_leagues = leagues[leagues['tier']=='professional'].sort_values(by='leagueid', ascending=False)
    
    # Create dictionaries 
    premium_dict = dict(zip(premium_leagues['name'],premium_leagues['leagueid']))
    professional_dict = dict(zip(professional_leagues['name'],professional_leagues['leagueid']))
    
    content = {
        'PREMIUM_LEAGUES':premium_dict,
        'PROFESSIONAL_LEAGUES':professional_dict
    }

    with open(league_constants_fpth, 'w') as file:
        yaml.safe_dump(content, file, default_flow_style=False)
        print("Value updated for league_ids")
        
@task        
async def fetch_hero_ids():
    file_path = 'constants.yml'
    
    # fetch hero constants from OpenDota's API
    heroes_constants = await get_opendota_df('constants/heroes')
    heroes_constants_transposed = heroes_constants.T
    hero_dict = dict(zip(heroes_constants_transposed['id'], heroes_constants_transposed['localized_name']))


    with open(hero_constants_fpth, 'r') as file:
        data = yaml.safe_load(file) or {}
        
    data["HEROES_CONSTANTS"] = hero_dict

    with open(hero_constants_fpth, 'w') as file:
        yaml.safe_dump(data, file)
        print("Values updated for HEROES_CONSTANTS")
        
@flow       
async def fetch_constants():
    await fetch_league_ids()
    await fetch_hero_ids() 
        
if __name__ == "__main__":
    asyncio.run(fetch_constants())