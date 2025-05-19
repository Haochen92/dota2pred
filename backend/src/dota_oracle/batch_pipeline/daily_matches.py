import asyncio
from prefect import flow, task 
from typing import List, Optional
import logging
from dota_oracle.utils.set_logging import get_logger
from dota_oracle.data_extraction.fetch_match_details import fetch_match_details
# to complete
from dota_oracle.data_repository

# Set up logger
logger = get_logger(__name__)
match_info_handler = logging.FileHandler(f'{ROOT_DIR}/logs/stored_pro_matchs.log')
handler_format = logging.Formatter('%(asctime)s - %(message)s')
match_info_handler.setFormatter(handler_format)
match_info_handler.addFilter(lambda record: record.levelno == logging.INFO)
logger.addHandler(match_info_handler)

# Constants
BATCH_SIZE = 10

@task
async def process_and_store_batch(match_ids: List[str]) -> Optional[List[int]]:
    match_records = []
    for match_id in match_ids:
        match_data = await get_match_details(match_id)
        if match_data is not None:
            match_records.append(match_data)
    
    if not match_records:
        return None
    
    try: 
        processed_matches = await insert_pro_matches(match_records)
        return processed_matches
    except Exception as e:
        logger.error(f'failed to insert into table with error: {e}')
        return None

    
@flow
async def fetch_daily_matches():
    batch_no = 0
    while True:
        try:
            match_ids = await promatch_ids_from_db(BATCH_SIZE)
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            return False
    
        if not match_ids:
            logger.info(f"No more matches left to process")
            return False

        processed_matches = await process_and_store_batch(match_ids)
        
        if processed_matches:
            try:
                success = await delete_processed_matches(processed_matches)
                if success:
                    batch_no += 1
                    logger.info(f"Successfully Stored batch {batch_no} ending match_id: {match_ids[-1]}")
                else:
                    logger.error(f"Failed to delete processed match IDs ending with: {match_ids[-1]}")
            except Exception as e:
                logger.error(f"Error deleting processed matches: {e}")


if __name__ == '__main__':
    asyncio.run(fetch_daily_matches())