import asyncio
import sys
from typing import TypeVar, Coroutine, Dict, Any
from utils.set_logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')

ASYNC_TASK = Coroutine[Any, Any, T]

async def run_tasks_concurrently(
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
    

async def run_tasks_as_group(
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

    
    
    