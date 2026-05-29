from typing import Any
from .primitive import Primitive


class ToggleFilter(Primitive):
    """Represents toggle_filter(change[, start]) — filtered version of toggle."""

    def __init__(self, change: Any, start: bool = False) -> None:
        self.change = change
        self.start = start

    def __repr__(self) -> str:
        return f"ToggleFilter({self.change!r}, start={self.start!r})"
