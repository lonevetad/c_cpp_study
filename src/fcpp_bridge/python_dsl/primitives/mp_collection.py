from typing import TypeVar, Generic, Callable, Any
from .primitive import Primitive

T = TypeVar("T")


class MpCollection(Primitive, Generic[T]):
    """Represents mp_collection(distance, value, null, accumulate, divide) — multi-path collection.
    ``accumulate`` and ``divide`` are callables (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (3, 4)   # accumulate, divide

    def __init__(self, distance: Any, value: T, null: T,
                 accumulate: Callable[[T, T], T], divide: Callable) -> None:
        self.distance = distance
        self.value = value
        self.null = null
        self.accumulate = accumulate
        self.divide = divide

    def __repr__(self) -> str:
        return f"MpCollection(distance={self.distance!r}, value={self.value!r}, accumulate=<callable>)"
