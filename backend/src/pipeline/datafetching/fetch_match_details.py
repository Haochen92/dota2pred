from prefect import flow, task 
import asyncio
import pandas as pd
import numpy as np
import logging
import pytz
from .opendota_api import fetch_opendota_api
from datetime import datetime, timedelta 
from src.config import ROOT_DIR
from src.utils.set_logging import get_logger
from src.postgresql import insert_to_table, fetch_promatch_ids
from prefect.cache_policies import INPUTS, TASK_SOURCE

# Set up logger
logger = get_logger(__name__)
match_info_handler = logging.FileHandler(f'{ROOT_DIR}/logs/stored_pro_matchs.log')
handler_format = logging.Formatter('%(asctime)s - %(message)s')
match_info_handler.setFormatter(handler_format)
match_info_handler.addFilter(lambda record: record.levelno == logging.INFO)
logger.addHandler(match_info_handler)

# Get the current date in YYYYMMDD format
timezone = pytz.timezone('Asia/Singapore')
current_date = datetime.now(timezone).strftime('%Y%m%d')

# Define paths
INPUT_FILE_PATH = ROOT_DIR / "data" / "pro_match_ids"/ f'dota2_pro_match_ids_{current_date}.csv'

BATCH_SIZE = 10

def pro_match_template():
    template = {
        'match_id': np.nan,
        'radiant_team_id': np.nan,
        'radiant_name': np.nan,
        'dire_team_id': np.nan,
        'dire_name': np.nan,
        'duration': np.nan,
        'start_time': np.nan,
        'radiant_win': np.nan
    }
    for i in list(range(0, 5)) + list(range(128, 133)):
        template[f"{i}_account_id"] = np.nan
        template[f"{i}_hero_id"] = np.nan
    return template

def populate_data_to_dict(dictionary, result):
    dictionary.update({
        'match_id': result.get('match_id', np.nan),
        'radiant_team_id': result.get('radiant_team_id', np.nan),
        'radiant_name': result.get('radiant_name', np.nan),
        'dire_team_id': result.get('dire_team_id', np.nan),
        'dire_name': result.get('dire_name', np.nan),
        'duration': result.get('duration', np.nan),
        'start_time': result.get('start_time', np.nan),
        'radiant_win': result.get('radiant_win', np.nan)
    })
    for player in result.get('players', {}):
        slot = player.get('player_slot')
        if slot is not None:
            dictionary[f"{slot}_account_id"] = player.get('account_id', np.nan)
            dictionary[f"{slot}_hero_id"] = player.get('hero_id', np.nan)

def extract_data_from_match_records(records):
    matches = []
    for record in records:
        if record is not None:
            match_dict = pro_match_template()
            populate_data_to_dict(match_dict, record)
            matches.append(match_dict)
        else:
            logger.error(f"Received NoneType result for match {record}")
    return matches


@task(retries=3, retry_delay_seconds=2, cache_policy=INPUTS + TASK_SOURCE, cache_expiration=timedelta(days=10))
async def get_match_details(match_id):
    url = f'http://api.opendota.com/api/matches/{match_id}'
    status, res = await fetch_opendota_api(url)
    
    if res and status == 200:
        return res
    else:
        logger.error(f"Failed with status code: {res.status_code if res else 'No response'}")

        return None    

@task
async def process_and_store_batch(match_ids):
    match_records = []
    for match_id in match_ids:
        match_data = await get_match_details(match_id)
        if match_data is not None:
            match_records.append(match_data)
    
    if not match_records:
        return None
    
    list_matches = extract_data_from_match_records(match_records)
    
    try: 
        insert_to_table('pro_matches', list_matches, 'match_id')
        return True
    except Exception as e:
        logger.error(f'failed to insert into table with error: {e}')
        return False

    
@flow
async def match_details_main():
    batch_no = 0
    while True:
        try:
            match_ids = fetch_promatch_ids(BATCH_SIZE)
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return False
    
        if not match_ids:
            logger.info(f"No more matches left to process")
            return False
    
        success = await process_and_store_batch(match_ids)
        if success:
            batch_no += 1
            logger.info(f"Successfully Stored batch {batch_no} ending match_id: {match_ids[-1]}")
        else:
            logger.error(f"Failed to store batch ending match_id: {match_ids[-1]}")


if __name__ == '__main__':
    asyncio.run(match_details_main())
