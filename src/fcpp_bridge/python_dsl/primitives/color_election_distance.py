from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class ColorElectionDistance(Primitive, Generic[T]):
    """Represents color_election_distance([value]) — color election with distance tracking."""

    def __init__(self, value: T = None) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"ColorElectionDistance(value={self.value!r})"
