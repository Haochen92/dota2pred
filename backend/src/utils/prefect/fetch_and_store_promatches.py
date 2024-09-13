from src.fetch_data.fetch_promatch import fetch_promatch_ids
from src.fetch_data.opendota_match_details import match_details_main
from prefect import flow
import asyncio


@flow
async def fetch_and_store_promatches():
    fetch_promatch_ids()
    await match_details_main()
    print("all jobs completed")
    
    
if __name__ == "__main__":
    asyncio.run(fetch_and_store_promatches())