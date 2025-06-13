from typing import TypeVar, Generic, Coroutine, Any, Optional
from pydantic import BaseModel, ConfigDict

T_Key = TypeVar("T_Key")
T_Result = TypeVar("T_Result")

# ===============================
#           Coroutines
# ===============================

class AsyncTask(BaseModel, Generic[T_Key, T_Result]):
    """A uniform way to represent a keyed, awaitable task.

    This class encapsulates a coroutine that can be run concurrently,
    identified by a unique key.

    Attributes:
        key (T_Key): The unique identifier for this task.
        coro (Coroutine): The awaitable coroutine function to be executed.
    """
    key: T_Key
    coro: Coroutine[Any, Any, T_Result]
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class TaskResult(BaseModel, Generic[T_Key, T_Result]):
    """A uniform way to represent the outcome of a completed task.

    This class holds either the successful result of a task or the
    exception that was raised during its execution.

    Attributes:
        key (T_Key): The unique identifier of the task this result belongs to.
        result (Optional[T_Result]): The return value of the coroutine if it
            succeeded. Defaults to None.
        exception (Optional[Exception]): The exception object if the coroutine
            failed. Defaults to None.
    """
    key: T_Key
    result: Optional[T_Result] = None
    exception: Optional[Exception] = None

    def get_result(self) -> Optional[T_Result]:
        """Returns the result, or raises the exception if the task failed."""
        if self.exception is not None:
            raise self.exception
        
        return self.result
    
    model_config = ConfigDict(arbitrary_types_allowed=True)