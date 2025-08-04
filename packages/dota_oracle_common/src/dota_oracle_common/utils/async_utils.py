import asyncio
import sys
from typing import List, Any, Optional, Coroutine
from .set_logging import get_logger
from dota_oracle_common.models.utils.schema import TaskResult, AsyncTask, T_Key, T_Result

logger = get_logger(__name__)


class TaskRunner:

    @staticmethod
    async def run_concurrently(
        tasks: List[AsyncTask[T_Key, T_Result]], concurrency_limit: Optional[int] = None
    ) -> List[TaskResult[T_Key, T_Result]]:
        """
        Run all tasks concurrently using asyncio.gather with an optional concurrency limit.
        Always returns a list of TaskResult objects, never raises.
        Exceptions are captured within the TaskResult object.
        """
        if not tasks:
            return []

        # Use a dictionary for fast lookup after gather completes
        task_keys = [task.key for task in tasks]

        if concurrency_limit:
            coroutines = TaskRunner._apply_semaphore(tasks, concurrency_limit)
        else:
            coroutines = [task.coro for task in tasks]

        results_or_exceptions = await asyncio.gather(*coroutines, return_exceptions=True)

        outcomes: List[TaskResult[T_Key, T_Result]] = []

        for i, outcome in enumerate(results_or_exceptions):
            key = task_keys[i]

            if isinstance(outcome, Exception):
                outcomes.append(TaskResult(key=key, exception=outcome))
            else:
                outcomes.append(TaskResult(key=key, result=outcome))

        return outcomes

    @staticmethod
    async def run_as_group(
        tasks: List[AsyncTask[T_Key, T_Result]], concurrency_limit: Optional[int] = None
    ) -> List[TaskResult[T_Key, T_Result]]:
        if sys.version_info < (3, 11):
            raise RuntimeError("TaskGroup requires Python 3.11 or newer.")
        if not tasks:
            return []

        if concurrency_limit:
            coroutines_to_run = TaskRunner._apply_semaphore(tasks, concurrency_limit)
        else:
            coroutines_to_run = [task.coro for task in tasks]

        task_to_key_map = {}

        # map the original keys to the new tasks
        original_keys = [task.key for task in tasks]

        async with asyncio.TaskGroup() as tg:
            asyncio_tasks = []
            for i, coro in enumerate(coroutines_to_run):
                t = tg.create_task(coro)
                asyncio_tasks.append(t)
                task_to_key_map[t] = original_keys[i]

        return [TaskResult(key=task_to_key_map[t], result=t.result()) for t in asyncio_tasks]

    @staticmethod
    def _apply_semaphore(tasks: List[AsyncTask[Any, Any]], concurrency_limit: int) -> List[Coroutine[Any, Any, Any]]:
        """Apply a semaphore to limit concurrency."""
        logger.info(f"Applying a concurrency limit of {concurrency_limit}.")
        semaphore = asyncio.Semaphore(concurrency_limit)

        async def wrapper(coro: Coroutine[Any, Any, Any]) -> Any:
            async with semaphore:
                return await coro

        # Apply the wrapper to each coroutine
        return [wrapper(task.coro) for task in tasks]
