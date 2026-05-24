from typing import Any
from .primitive import Primitive


class Toggle(Primitive):
    """Represents toggle(change[, start]) — toggles a boolean on each change event."""

    def __init__(self, change: Any, start: bool = False) -> None:
        self.change = change
        self.start = start

    def __repr__(self) -> str:
        return f"Toggle({self.change!r}, start={self.start!r})"
