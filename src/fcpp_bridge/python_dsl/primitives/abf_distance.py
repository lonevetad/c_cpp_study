from typing import Callable
from .primitive import Primitive


class AbfDistance(Primitive):
    """Represents abf_distance(source[, metric]) — Adaptive Bellman-Ford distance.
    ``metric`` is an optional callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (1,)   # metric at constructor index 1

    def __init__(self, source: bool, metric: Callable = None) -> None:
        self.source = source
        self.metric = metric

    def __repr__(self) -> str:
        return f"AbfDistance(source={self.source!r})"
