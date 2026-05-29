from typing import Any
from .primitive import Primitive


class Counter(Primitive):
    """Represents counter([start[, increment]]) — increment counter each round."""

    def __init__(self, start: Any = None, increment: Any = None) -> None:
        self.start = start
        self.increment = increment

    def __repr__(self) -> str:
        return f"Counter(start={self.start!r})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Counter) and self.start == other.start
