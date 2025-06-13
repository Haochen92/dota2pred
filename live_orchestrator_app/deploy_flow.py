from prefect import flow
from prefect.runner.storage import GitRepository
from prefect_github import GitHubCredentials    
from prefect.blocks.system import Secret



if __name__ == "__main__":
    github_token = Secret.load("github")
    flow.from_source(
        source=GitRepository(
            url="https://github.com/Haochen92/dota2pred.git",
            branch='remote',
            credentials={"access_token":github_token}
            ),
        entrypoint="backend/src/prefect/fetch_and_store_promatches.py:fetch_and_store_promatches"
        ).deploy(
        name="fetch-promatches-deployment",
        work_pool_name="work-pool",
        cron="0 0 * * *" 
    )
