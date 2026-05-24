from typing import Any
from .primitive import Primitive


class TimeSince(Primitive):
    """Represents time_since(condition) — time elapsed since condition was true."""

    def __init__(self, condition: Any) -> None:
        self.condition = condition

    def __repr__(self) -> str:
        return f"TimeSince({self.condition!r})"
