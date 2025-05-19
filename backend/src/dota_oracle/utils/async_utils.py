import asyncio
import sys
from typing import TypeVar, Coroutine, Dict, Any, List
from .set_logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

ASYNC_TASK = Coroutine[Any, Any, T]

async def get_outcome_concurrently(
    keyed_coroutines: Dict[str, ASYNC_TASK]
) -> Dict[str, T|Exception]:
    
    if not keyed_coroutines:
        return {}
    
    keys, values = zip(*keyed_coroutines.items())
    task_keys = list(keys)
    coroutines = list(values)
    
    res_list = await asyncio.gather(
        *coroutines, 
        return_exceptions=True
    )
    
    # Process outcomes
    outcome_dict: Dict[str, T|Exception] = {}
    error_count = 0
    success_count = 0
    
    for task_name, task_outcome in zip(task_keys, res_list):
        outcome_dict[task_name] = task_outcome
        if isinstance(task_outcome, Exception):
            logger.error(f"task {task_name} has failed with exception {task_outcome}")
            error_count += 1
        else:
            success_count += 1
        
    logger.info(f"tasks run completed with {success_count} completed and {error_count} failed")
    
    return outcome_dict
    

async def get_outcome_as_group(
    keyed_coroutines: Dict[str, ASYNC_TASK]
) -> Dict[str, T]| Exception:
    
    if sys.version_info < (3, 11):
        raise RuntimeError("asyncio.TaskGroup requires Python 3.11 or newer.")
    
    created_tasks: Dict[str, asyncio.Task[T]] = {}
    
    async with asyncio.TaskGroup() as tg:
        for key, coro in keyed_coroutines.items():
            created_tasks[key] = tg.create_task(coro)
    

    results_dict: Dict[str, T] = {}
    for key, task_obj in created_tasks.items():
        results_dict[key] = await task_obj
        

    return results_dict

    
async def run_updates_concurrently(
    update_coroutines: List[Coroutine[Any, Any, Any]],
) -> None:
    """
    Runs a list of update coroutines concurrently.
    All coroutines are attempted. Errors are logged.
    Does not return any values.
    """
    if not update_coroutines:
        return

    results_or_exceptions = await asyncio.gather(
        *update_coroutines, 
        return_exceptions=True
    )
    
    success_count = 0
    
    exceptions_encountered: List[BaseException] = []
    for i, outcome in enumerate(results_or_exceptions):
        if isinstance(outcome, Exception):
            logger.warning(f"Update task at index {i} failed: {type(outcome).__name__} - {outcome}")
            exceptions_encountered.append(outcome)
        else:
            success_count += 1
    
    error_count = len(exceptions_encountered)
        
    logger.info(f"Update tasks completed. Successful: {success_count}, Failed: {error_count}.")
    if exceptions_encountered:
        raise ExceptionGroup(f"{error_count} update tasks failed")

async def run_updates_as_group(
    update_coroutines: List[Coroutine[Any, Any, Any]]
) -> None:
    """
    Runs a list of update coroutines using asyncio.TaskGroup.
    If ANY task fails, TaskGroup will raise that task's exception (or an ExceptionGroup),
    and other tasks in the group will be cancelled. This function allows that exception
    to propagate.
    If all succeed, the function completes silently.
    Requires Python 3.11+.
    """
    if sys.version_info < (3, 11):
        raise RuntimeError("asyncio.TaskGroup requires Python 3.11 or newer.")
    
    if not update_coroutines:
        return

    try:
        async with asyncio.TaskGroup() as tg:
            logger.info(f"TaskGroup active for updates. Creating {len(update_coroutines)} tasks...") # Placeholder
            for i, coro in enumerate(update_coroutines):
                tg.create_task(coro) 
            logger.info("All update tasks created in TaskGroup. Waiting for completion...")
           
        logger.info("TaskGroup for updates completed successfully. All updates presumed successful.")
    except Exception as e:
        print(f"TaskGroup for updates encountered an error: {type(e).__name__} - {e}")
        raise 

    