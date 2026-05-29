from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class DiameterElectionDistance(Primitive, Generic[T]):
    """Represents diameter_election_distance(value, diameter) — diameter election with distance tracking."""

    def __init__(self, value: T, diameter: int) -> None:
        self.value = value
        self.diameter = diameter

    def __repr__(self) -> str:
        return f"DiameterElectionDistance(value={self.value!r}, diameter={self.diameter!r})"
