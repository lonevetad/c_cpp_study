from typing import TypeVar, Generic, Callable, Any
from .primitive import Primitive

T = TypeVar("T")


class SpCollection(Primitive, Generic[T]):
    """Represents sp_collection(distance, value, null, accumulate) — single-path collection.
    ``accumulate`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (3,)   # accumulate at constructor index 3

    def __init__(self, distance: Any, value: T, null: T, accumulate: Callable[[T, T], T]) -> None:
        self.distance = distance
        self.value = value
        self.null = null
        self.accumulate = accumulate

    def __repr__(self) -> str:
        return f"SpCollection(distance={self.distance!r}, value={self.value!r}, accumulate=<callable>)"
