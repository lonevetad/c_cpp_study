from typing import Any
from .primitive import Primitive


class StateValue(Primitive):
    """Marker for current node's own state value."""

    def __init__(self) -> None:
        pass

    def __repr__(self) -> str:
        return "StateValue()"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, StateValue)
