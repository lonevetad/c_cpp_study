from typing import Callable
from .primitive import Primitive


class BisDistance(Primitive):
    """Represents bis_distance(source, period, speed[, metric]) — Bounded Information Speeds distance.
    ``metric`` is an optional callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (3,)   # metric at constructor index 3

    def __init__(self, source: bool, period: float, speed: float,
                 metric: Callable = None) -> None:
        self.source = source
        self.period = period
        self.speed = speed
        self.metric = metric

    def __repr__(self) -> str:
        return f"BisDistance(source={self.source!r}, period={self.period!r}, speed={self.speed!r})"
