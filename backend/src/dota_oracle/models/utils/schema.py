from typing import TypeVar, Generic, Coroutine, Any, Optional
from pydantic import BaseModel, ConfigDict

T_Key = TypeVar("T_Key")
T_Result = TypeVar("T_Result")

# ===============================
#           Coroutines
# ===============================

class AsyncTask(BaseModel, Generic[T_Key, T_Result]):
    """A uniform way to represent a keyed, awaitable task."""
    key: T_Key
    coro: Coroutine[Any, Any, T_Result]
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

class TaskResult(BaseModel, Generic[T_Key, T_Result]):
    """A uniform way to represent the outcome of a task."""
    key: T_Key
    result: Optional[T_Result] = None
    exception: Optional[Exception] = None

    def get_result(self) -> Optional[T_Result]:
        """Returns the result, or raises the exception if the task failed."""
        if self.exception is not None:
            raise self.exception
        
        return self.result
    
    model_config = ConfigDict(arbitrary_types_allowed=True)