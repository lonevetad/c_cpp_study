from typing import Any
from .primitive import Primitive


class SharedClock(Primitive):
    """Represents shared_clock() — synchronized network-wide clock."""

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "SharedClock()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, SharedClock)
