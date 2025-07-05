import asyncio
import sys
from typing import List, Any
from .set_logging import get_logger
from ..models.utils import TaskResult, AsyncTask

logger = get_logger(__name__)


class TaskRunner:

    @staticmethod
    async def run_concurrently(tasks: List[AsyncTask[Any, Any]]) -> List[TaskResult[Any, Any]]:
        """
        Run all tasks concurrently using asyncio.gather
        Always returns a list of TaskResult objects, never raises.
        Exceptions are captured within the TaskResult object.
        """
        if not tasks:
            return []

        # Use a dictionary for fast lookup after gather completes
        task_keys = [task.key for task in tasks]
        coroutines = [task.coro for task in tasks]

        results_or_exceptions = await asyncio.gather(*coroutines, return_exceptions=True)

        outcomes: List[TaskResult[Any, Any]] = []

        for i, outcome in enumerate(results_or_exceptions):
            key = task_keys[i]

            if isinstance(outcome, Exception):
                outcomes.append(TaskResult(key=key, exception=outcome))
            else:
                outcomes.append(TaskResult(key=key, result=outcome))

        return outcomes

    @staticmethod
    async def run_as_group(tasks: List[AsyncTask[Any, Any]]) -> List[TaskResult[Any, Any]]:
        if sys.version_info < (3, 11):
            raise RuntimeError("TaskGroup requires Python 3.11 or newer.")

        if not tasks:
            return []

        task_to_key_map = {}

        try:
            async with asyncio.TaskGroup() as tg:
                asyncio_tasks = []
                for task_model in tasks:
                    t = tg.create_task(task_model.coro)
                    asyncio_tasks.append(t)
                    task_to_key_map[t] = task_model.key
        except* Exception as eg:
            logger.error(f"TaskGroup failed with {len(eg.exceptions)} error(s).")
            raise eg

        # If we reach here, all tasks succeeded
        return [TaskResult(key=task_to_key_map[t], result=t.result()) for t in asyncio_tasks]
