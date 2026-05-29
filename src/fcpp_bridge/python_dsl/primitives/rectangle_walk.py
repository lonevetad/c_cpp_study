from typing import Any
from .primitive import Primitive


class RectangleWalk(Primitive):
    """Represents rectangle_walk(low, hi, max_v, period) — random walk bounded to a rectangle."""

    def __init__(self, low: Any, hi: Any, max_v: float, period: float) -> None:
        self.low = low
        self.hi = hi
        self.max_v = max_v
        self.period = period

    def __repr__(self) -> str:
        return f"RectangleWalk(low={self.low!r}, hi={self.hi!r}, max_v={self.max_v!r})"
