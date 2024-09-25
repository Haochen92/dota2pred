from prefect import flow

if __name__ == "__main__":
    flow.from_source(
        source="https://github.com/Haochen92/dota2pred.git",
        branch="remote",
        access_token='{{prefect.blocks.secret.github}}',
        entrypoint="backend/src/prefect/fetch_and_store_promatches.py:fetch_and_store_promatches"
        ).deploy(
        name="fetch-promatches-deployment",
        work_pool_name="work-pool",
        cron="0 0 * * *" 
    )
