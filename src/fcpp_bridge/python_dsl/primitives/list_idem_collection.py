from typing import TypeVar, Generic, Callable
from .primitive import Primitive

T = TypeVar("T")


class ListIdemCollection(Primitive, Generic[T]):
    """Represents list_idem_collection(distance, value, radius, speed, null, epsilon, accumulate).
    ``accumulate`` is a callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (6,)   # accumulate at constructor index 6

    def __init__(self, distance: float, value: T, radius: float, speed: float,
                 null: T, epsilon: float, accumulate: Callable) -> None:
        self.distance = distance
        self.value = value
        self.radius = radius
        self.speed = speed
        self.null = null
        self.epsilon = epsilon
        self.accumulate = accumulate

    def __repr__(self) -> str:
        return f"ListIdemCollection(distance={self.distance!r}, value={self.value!r}, accumulate=<callable>)"
