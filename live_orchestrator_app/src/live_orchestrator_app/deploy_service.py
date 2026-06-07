import asyncio
from prefect import flow
from prefect.client.orchestration import get_client
from prefect.client.schemas.filters import (
    FlowRunFilter,
    FlowRunFilterDeploymentId,
    FlowRunFilterState,
    FlowRunFilterStateType,
)
from dota_oracle_common.utils.set_logging import get_logger

logger = get_logger(__name__)

DEPLOYMENT_FULL_NAME = "start live orchestrator/live_orchestration_app"


async def _crash_orphaned_runs() -> None:
    """Crash any non-terminal runs of this deployment left over from a previous container.

    A deploy recreates this container, which kills the worker mid-cycle. Prefect can't
    always mark the in-flight run terminal within docker's stop grace period, so it lingers
    as a RUNNING zombie and blocks the pool's concurrency=1 slot. We run on startup (before
    the worker), so any non-terminal run here is by definition an orphan -- crash it.

    Uses the REST set_state endpoint directly to avoid a client-side State model-rebuild bug.
    """
    try:
        async with get_client() as client:
            deployment = await client.read_deployment_by_name(DEPLOYMENT_FULL_NAME)
            flt = FlowRunFilter(
                deployment_id=FlowRunFilterDeploymentId(any_=[deployment.id]),
                state=FlowRunFilterState(type=FlowRunFilterStateType(any_=["RUNNING", "PENDING", "CANCELLING"])),
            )
            orphans = await client.read_flow_runs(flow_run_filter=flt)
            for run in orphans:
                await client._client.post(
                    f"/flow_runs/{run.id}/set_state",
                    json={
                        "state": {
                            "type": "CRASHED",
                            "name": "Crashed",
                            "message": "Orphaned by container restart; cleared on startup.",
                        },
                        "force": True,
                    },
                )
                logger.info(f"Cleared orphaned flow run '{run.name}' left over from a previous container.")
            if not orphans:
                logger.info("No orphaned live-orchestrator runs to clear on startup.")
    except Exception as e:
        # Never block startup on cleanup; the worker can still come up.
        logger.warning(f"Orphaned-run cleanup skipped due to error: {e}", exc_info=True)


async def create_deployment():
    """
    Builds a Prefect Deployment object with a specific entrypoint
    and applies it to the Prefect server.
    """

    flow_from_file = await flow.from_source(
        source="./",
        entrypoint="live_orchestrator_app/app_container.py:start_application",
    )  # type: ignore

    await flow_from_file.deploy(
        name="live_orchestration_app", work_pool_name="dota-work-pool", cron="*/2 * * * *", concurrency_limit=1
    )  # type: ignore
    logger.info("Prefect Deployment 'live_orchestration_app' applied successfully.")

    # Free the concurrency slot from any run orphaned by this container's restart.
    await _crash_orphaned_runs()


if __name__ == "__main__":
    asyncio.run(create_deployment())
