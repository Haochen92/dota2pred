import asyncio
from typing import List, Any, Optional, Coroutine
from .set_logging import get_logger
from dota_oracle_common.models.utils.schema import TaskResult, AsyncTask, T_Key, T_Input, T_Result

logger = get_logger(__name__)


class TaskRunner:

    @staticmethod
    async def run_concurrently(
        tasks: List[AsyncTask[T_Key, T_Input, T_Result]], concurrency_limit: Optional[int] = None
    ) -> List[TaskResult[T_Key, T_Input, T_Result]]:
        """
        Run all tasks concurrently using asyncio.gather with an optional concurrency limit.
        Always returns a list of TaskResult objects, never raises.
        Exceptions are captured within the TaskResult object.
        """
        if not tasks:
            return []

        # Use a dictionary for fast lookup after gather completes
        coroutines = [task.coro for task in tasks]

        if concurrency_limit:
            coroutines = TaskRunner._apply_semaphore(tasks, concurrency_limit)
        else:
            coroutines = [task.coro for task in tasks]

        results_or_exceptions = await asyncio.gather(*coroutines, return_exceptions=True)

        outcomes = [
            TaskResult(key=task.key, inputs=task.inputs, outcome=outcome)
            for task, outcome in zip(tasks, results_or_exceptions)
        ]

        return outcomes

    @staticmethod
    def _apply_semaphore(
        tasks: List[AsyncTask[Any, Any, Any]], concurrency_limit: int
    ) -> List[Coroutine[Any, Any, Any]]:
        """Apply a semaphore to limit concurrency."""
        logger.info(f"Applying a concurrency limit of {concurrency_limit}.")
        semaphore = asyncio.Semaphore(concurrency_limit)

        async def wrapper(coro: Coroutine[Any, Any, Any]) -> Any:
            async with semaphore:
                return await coro

        # Apply the wrapper to each coroutine
        return [wrapper(task.coro) for task in tasks]
