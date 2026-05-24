from typing import Any
from .primitive import Primitive


class CountHood(Primitive):
    """Represents count_hood() — count of neighbors."""

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "CountHood()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, CountHood)
