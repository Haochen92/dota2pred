from prefect import task, flow
from prefect.cache_policies import INPUTS, TASK_SOURCE
import pandas as pd
import time 
import yaml
import requests
from retry import retry
from datetime import datetime, timedelta
from src.config import ROOT_DIR
from src.utils.set_logging import get_logger
import pytz

# Config logging
logger = get_logger(__name__)

# Get the current date in YYYYMMDD format
timezone = pytz.timezone('Asia/Singapore')
current_date = datetime.now(timezone).strftime('%Y%m%d')

# Define paths
root_path = ROOT_DIR
constants_file_path = root_path / 'constants' / 'constants.yml'
output_file_path = root_path / 'data' / 'pro_match_ids' / f'dota2_pro_match_ids_{current_date}.csv'

    

BASE_URL = 'https://api.opendota.com/api/proMatches'
PARAMETER_STRING = '?less_than_match_id='
MAX_MATCH_ID_INITIAL = 9999999999999
SLEEP_DURATION = 3.5
OUTPUT_COLUMNS = [
    'match_id', 'radiant_name', 'radiant_team_id', 'dire_name', 
    'dire_team_id', 'leagueid', 'league_name', 'start_time', 'radiant_win'
]

@task(retries=3, retry_delay_seconds=2, cache_policy=INPUTS + TASK_SOURCE, cache_expiration=timedelta(days=1))
def fetch_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        logger.error(err)
        raise RuntimeError(f"HTTP error occurred when accessing {url}: {err}")
    except requests.exceptions.RequestException as e:
        logger.error(err)
        raise RuntimeError(f"An error occurred when accessing {url}: {e}")

@task(cache_policy=INPUTS + TASK_SOURCE, cache_expiration=timedelta(days=1))
def save_to_csv(data_json, include_header=True):
    '''
    Saves json data to csv file. Will only include headers columns for the first iteration. 
    '''
    selected_json = [{col: x[col] for col in OUTPUT_COLUMNS} for x in data_json]
    output = pd.DataFrame(selected_json)
    output.to_csv(output_file_path, encoding='utf-8', mode='a', index=False, header=include_header)


@flow   
def fetch_promatch_ids(): 
    min_match_id = 0 
    with open(constants_file_path, 'r') as file:
        data = yaml.safe_load(file)
        min_match_id = data.get("LAST_MATCH_ID", min_match_id)

    max_match_id = MAX_MATCH_ID_INITIAL
    first_iteration = True # Flag to check for the first iteration
    initial_max_match_id = None # Placeholder for max_match_id to update min_match_id

    while max_match_id > min_match_id:
        search_url = BASE_URL + PARAMETER_STRING + str(max_match_id)
        logger.info(f"Requesting: {search_url}")

        data_json = fetch_data(search_url)

        if not data_json:
            continue
        
        save_to_csv(data_json, include_header=first_iteration)
        
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


if __name__ == "__main__":
    fetch_promatch_ids()
