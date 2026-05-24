from typing import Callable
from .primitive import Primitive


class FlexDistance(Primitive):
    """Represents flex_distance(source, epsilon, radius, distortion, frequency[, metric]).
    ``metric`` is an optional callable (C++ ``G&&``)."""

    has_callable_args = True
    callable_arg_positions = (5,)   # metric at constructor index 5

    def __init__(self, source: bool, epsilon: float, radius: float,
                 distortion: float, frequency: int, metric: Callable = None) -> None:
        self.source = source
        self.epsilon = epsilon
        self.radius = radius
        self.distortion = distortion
        self.frequency = frequency
        self.metric = metric

    def __repr__(self) -> str:
        return f"FlexDistance(source={self.source!r}, radius={self.radius!r})"
