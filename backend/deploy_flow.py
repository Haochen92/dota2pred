# deploy_flow.py
from src.prefect.fetch_and_store_promatches import fetch_and_store_promatches  # Import the flow

if __name__ == "__main__":
    fetch_and_store_promatches.deploy(
        name="fetch-promatches-deployment",
        work_pool_name="docker-pool",
        image="gengie/fetch_and_store_promatches:latest",
        build=True,
        cron="0 0 * * *" 
    )
