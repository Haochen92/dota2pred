from typing import TypeVar, Generic, Coroutine, Any, Union
from pydantic import BaseModel, ConfigDict

T_Key = TypeVar("T_Key")
T_Input = TypeVar("T_Input")
T_Result = TypeVar("T_Result")

# ===============================
#           Coroutines
# ===============================


class AsyncTask(BaseModel, Generic[T_Key, T_Input, T_Result]):
    """A uniform way to represent a keyed, awaitable task.

    This class encapsulates a coroutine that can be run concurrently,
    identified by a unique key.

    Attributes:
        key (T_Key): The unique identifier for this task.
        inputs (T_Input): The inputs for this task
        coro (Coroutine): The awaitable coroutine function to be executed.
    """

    key: T_Key
    inputs: T_Input
    coro: Coroutine[Any, Any, T_Result]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TaskResult(BaseModel, Generic[T_Key, T_Input, T_Result]):
    """
    Represents the complete outcome of a task, including its inputs and outcome.
    The `outcome` field holds either the successful result or the exception.
    """

    key: T_Key
    inputs: T_Input
    outcome: Union[T_Result, BaseException]

    model_config = ConfigDict(arbitrary_types_allowed=True)
