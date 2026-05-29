from typing import Any
from .primitive import Primitive


class RandomRectangleTarget(Primitive):
    """Represents random_rectangle_target(low, hi[, reach]) — pick a random target in a rectangle."""

    def __init__(self, low: Any, hi: Any, reach: float = None) -> None:
        self.low = low
        self.hi = hi
        self.reach = reach

    def __repr__(self) -> str:
        return f"RandomRectangleTarget(low={self.low!r}, hi={self.hi!r})"
