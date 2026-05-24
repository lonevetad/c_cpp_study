from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class ColorElection(Primitive, Generic[T]):
    """Represents color_election([value]) — color-based leader election."""

    def __init__(self, value: T = None) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"ColorElection(value={self.value!r})"
