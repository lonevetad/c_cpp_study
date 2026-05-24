from typing import TypeVar, Generic, Callable
from .primitive import Primitive

T = TypeVar("T")


class WmpCollection(Primitive, Generic[T]):
    """Represents wmp_collection(distance, radius, value, accumulate, multiply) — weighted multi-path collection.
    ``accumulate`` and ``multiply`` are callables (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (3, 4)   # accumulate, multiply

    def __init__(self, distance: float, radius: float, value: T,
                 accumulate: Callable[[T, T], T], multiply: Callable) -> None:
        self.distance = distance
        self.radius = radius
        self.value = value
        self.accumulate = accumulate
        self.multiply = multiply

    def __repr__(self) -> str:
        return (
            f"WmpCollection(distance={self.distance!r}, radius={self.radius!r}, "
            f"value={self.value!r}, accumulate=<callable>)"
        )
