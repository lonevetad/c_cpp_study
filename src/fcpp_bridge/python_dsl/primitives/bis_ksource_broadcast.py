from typing import TypeVar, Generic, Callable
from .primitive import Primitive

T = TypeVar("T")


class BisKsourceBroadcast(Primitive, Generic[T]):
    """Represents bis_ksource_broadcast(source, value, k, period, speed[, metric]).
    ``metric`` is an optional callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (5,)   # metric at constructor index 5

    def __init__(self, source: bool, value: T, k: int, period: float,
                 speed: float, metric: Callable = None) -> None:
        self.source = source
        self.value = value
        self.k = k
        self.period = period
        self.speed = speed
        self.metric = metric

    def __repr__(self) -> str:
        return f"BisKsourceBroadcast(source={self.source!r}, k={self.k!r}, value={self.value!r})"
