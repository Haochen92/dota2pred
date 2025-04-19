from prefect import flow
from src.postgresql import get_async_session
from database.schemas.matches import ProMatchID
from sqlalchemy.dialects.postgresql import insert
import asyncio
import time 
import yaml
from datetime import datetime
from src.config import ROOT_DIR
from src.utils.set_logging import get_logger
from data_pipeline.fetching.api.opendota_api import fetch_opendota
import pytz

# Config logging
logger = get_logger(__name__)

# Get the current date in YYYYMMDD format
timezone = pytz.timezone('Asia/Singapore')
current_date = datetime.now(timezone).strftime('%Y%m%d')

# Define paths
root_path = ROOT_DIR
constants_file_path = root_path / 'constants' / 'constants.yml'

    
# Constants
ENDPOINT = '/proMatches'
MAX_MATCH_ID_INITIAL = 9999999999999
SLEEP_DURATION = 3.5
OUTPUT_COLUMNS = [
    'match_id', 'radiant_name', 'radiant_team_id', 'dire_name', 
    'dire_team_id', 'leagueid', 'league_name', 'start_time', 'radiant_win'
]


@flow   
async def fetch_promatch_ids(): 
    min_match_id = 0 
    with open(constants_file_path, 'r') as file:
        data = yaml.safe_load(file)
        min_match_id = data.get("LAST_MATCH_ID", min_match_id)

    max_match_id = MAX_MATCH_ID_INITIAL
    first_iteration = True # Flag to check for the first iteration
    initial_max_match_id = None # Placeholder for max_match_id to update min_match_id

    while max_match_id > min_match_id:
        logger.info(f"Requesting: {str(max_match_id)}")

        data_json = await fetch_opendota(
            endpoint=ENDPOINT,
            params= {'less_than_match_id':max_match_id}
        )

        if not data_json:
            continue
        
        await insert_promatch_ids(data_json)
        
        
        if first_iteration:
            initial_max_match_id = max([x['match_id'] for x in data_json])
            first_iteration = False  # Update the flag after capturing the value
        
        max_match_id = min([x['match_id'] for x in data_json])
        logger.info("Sleeping...")
        time.sleep(SLEEP_DURATION)
    
    if initial_max_match_id:  # Ensure it was captured
        with open(constants_file_path, 'w') as file:
            data["LAST_MATCH_ID"] = initial_max_match_id
            yaml.safe_dump(data, file)

async def insert_promatch_ids(data_json):
    '''
    Saves match IDs from json data to the PostgreSQL database
    '''
    async with get_async_session() as session:
        try:
            match_ids = [{"match_id": x['match_id']} for x in data_json]
            stmt = insert(ProMatchID).values(match_ids).on_conflict_do_nothing(
                index_elements=["match_id"]
            )
            await session.execute(stmt)
            await session.commit()
        
        except Exception as e:
            logger.error(f"failed to insert promatch_id into database {e}")
            raise

if __name__ == "__main__":
    asyncio.run(fetch_promatch_ids())
