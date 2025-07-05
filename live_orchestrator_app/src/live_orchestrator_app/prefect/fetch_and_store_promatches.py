from dota_oracle_pipeline.data_extraction.fetch_pro_match import fetch_promatch_ids
from dota_oracle_pipeline.data_extraction.fetch_match_details import match_details_main
from dota_oracle_pipeline.data_extraction.fetch_constants import fetch_constants
from prefect import flow
import asyncio


@flow(log_prints=True)
async def fetch_and_store_promatches():
    fetch_constants()
    fetch_promatch_ids()
    await match_details_main()
    print("all jobs completed")


if __name__ == "__main__":
    asyncio.run(fetch_and_store_promatches())
