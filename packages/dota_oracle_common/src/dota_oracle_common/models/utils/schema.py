from typing import TypeVar, Generic, Coroutine, Any, Optional, cast
from pydantic import BaseModel, ConfigDict, model_validator

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
    key: T_Key
    result: Optional[T_Result] = None
    exception: Optional[Exception] = None

    @model_validator(mode="after")
    def validate_result_or_exception(self):
        if self.result is None and self.exception is None:
            raise ValueError("Either result or exception must be set")
        if self.result is not None and self.exception is not None:
            raise ValueError("Cannot have both result and exception")
        return self

    def get_result(self) -> T_Result:
        if self.exception is not None:
            raise self.exception
        # Type checker knows result can't be None here due to validator
        return cast(T_Result, self.result)

    model_config = ConfigDict(arbitrary_types_allowed=True)
