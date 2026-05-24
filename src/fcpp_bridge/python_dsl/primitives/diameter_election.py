from typing import TypeVar, Generic
from .primitive import Primitive

T = TypeVar("T")


class DiameterElection(Primitive, Generic[T]):
    """Represents diameter_election(value, diameter) — elect node by maximum diameter."""

    def __init__(self, value: T, diameter: int) -> None:
        self.value = value
        self.diameter = diameter

    def __repr__(self) -> str:
        return f"DiameterElection(value={self.value!r}, diameter={self.diameter!r})"
