from dota_oracle_pipeline.data_extraction.fetch_pro_match import fetch_pro_match
from dota_oracle_pipeline.data_extraction.fetch_match_details import fetch_match_details
from dota_oracle_pipeline.data_extraction.fetch_constants import fetch_constants
from prefect import flow
import asyncio


@flow(log_prints=True)
async def fetch_and_store_promatches() -> None:
    fetch_constants()
    await fetch_pro_match(max_match_id=1000000, min_match_id=1)
    # await fetch_match_details(match_id=123)  # Example usage
    print("all jobs completed")


if __name__ == "__main__":
    asyncio.run(fetch_and_store_promatches())
